#!/usr/bin/env python3
import json
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path


def replace_placeholders(template: str, values: list) -> str:
    if template is None:
        return ''

    # match [0], [+0], [-0] etc.
    pat = re.compile(r'\[([+-]?)(\d+)\]')

    def _repl(m):
        sign = m.group(1)
        idx = int(m.group(2))
        try:
            v = values[idx]
        except Exception:
            return ''
        # sentinel 65535 means '無' -> skip (only for numeric types)
        if isinstance(v, int) and v == 65535:
            return ''
        # prepare string form
        s = str(v)
        # apply sign handling only for numeric values
        if sign == '+':
            if isinstance(v, (int, float)):
                try:
                    if float(v) >= 0:
                        return f'+{s}'
                except Exception:
                    return f'+{s}'
                return s
            return s
        if sign == '-':
            if isinstance(v, (int, float)):
                return f'-{s}'
            return s
        return s

    return pat.sub(_repl, template)


def process(item_data: dict, textdata: dict) -> dict:
    # textdata groups
    g357 = textdata.get('357') or textdata.get(357) or {}
    g175 = textdata.get('175') or textdata.get(175) or {}

    out = {}
    # helper: read Need fields with alternative names used in 2.json
    # return None when missing so caller can detect pairs
    def _read_need(obj, primary, alt, default=None):
        if primary in obj:
            return obj[primary]
        if alt in obj:
            return obj[alt]
        return default
    for id_str, item in item_data.items():
        try:
            fields = item.get('fields', {})
        except AttributeError:
            fields = {}

        entry = {}
        # basic passthrough fields in specific order so we can insert attack info
        # NOTE: do not include BasePrice or Durable in output (they are not needed)
        # add Index, Name, Type in that order
        if 'Index' in fields:
            entry['Index'] = fields['Index']
        if 'Name' in fields:
            entry['Name'] = fields['Name']
        if 'Type' in fields:
            entry['Type'] = fields['Type']

        # insert attack info immediately after Type when attack-related fields exist.
        # Show attack info whenever LowAP/HighAP or AttackSpeed_raw or AttackRange is present and valid.
        def _valid_value(v):
            if v is None:
                return False
            try:
                vi = int(v)
            except Exception:
                try:
                    vf = float(v)
                    vi = int(vf)
                except Exception:
                    return True
            if vi == 0 or vi == 65535:
                return False
            return True

        low_present = _valid_value(fields.get('LowAP'))
        high_present = _valid_value(fields.get('HighAP'))
        speed_present = _valid_value(fields.get('AttackSpeed_raw'))
        range_present = _valid_value(fields.get('AttackRange'))

        if low_present or high_present or speed_present or range_present:
            low = fields.get('LowAP')
            high = fields.get('HighAP')

            def _num_to_str(x):
                try:
                    return str(int(x))
                except Exception:
                    try:
                        return str(float(x))
                    except Exception:
                        return str(x)

            attack_parts = []
            if low_present or high_present:
                if low_present and high_present:
                    try:
                        li = int(low); hi = int(high)
                        if li == hi:
                            attack_parts.append(f"{li}")
                        else:
                            mn, mx = min(li,hi), max(li,hi)
                            attack_parts.append(f"{mn}~{mx}")
                    except Exception:
                        attack_parts.append(f"{_num_to_str(low)}~{_num_to_str(high)}")
                else:
                    v = low if low_present else high
                    attack_parts.append(_num_to_str(v))

            speed_sec = None
            if speed_present:
                try:
                    speed_sec = float(fields.get('AttackSpeed_raw')) / 100.0
                except Exception:
                    speed_sec = None

            if attack_parts:
                if speed_sec is not None:
                    entry['攻撃力'] = f"{attack_parts[0]} ({speed_sec:.2f} 秒)"
                else:
                    entry['攻撃力'] = f"{attack_parts[0]}"
            elif speed_sec is not None:
                entry['攻撃力'] = f"({speed_sec:.2f} 秒)"

            if range_present:
                try:
                    entry['射程'] = int(fields.get('AttackRange'))
                except Exception:
                    entry['射程'] = fields.get('AttackRange')

        # then add remaining passthrough keys
        for key in ('RequiredLevel', 'RequiredStatus', 'StackableNum', 'DropLevel', 'DropCoefficient'):
            if key in fields:
                entry[key] = fields[key]

        # ensure requirements is preserved: it may exist at top-level `item` rather than inside `fields`
        # Preserve the key if it exists in either place (even if empty), to match expected schema.
        if 'requirements' in item:
            entry['requirements'] = item.get('requirements')
        elif 'requirements' in fields:
            entry['requirements'] = fields.get('requirements')

        # unique_effects -> use group 357
        uefs = item.get('unique_effects') or []
        ue_texts = []
        for idx, ue in enumerate(uefs):
            eff = ue.get('EffectID')
            if eff is None or eff == 65535:
                continue
            tmpl = None
            # keys in textdata are strings
            tmpl = g357.get(str(eff)) if isinstance(g357, dict) else None
            if not tmpl:
                tmpl = g357.get(eff) if isinstance(g357, dict) else None
            if not tmpl:
                continue
            # build pairs (Need0/Need1) and (Need2/Need3)
            a0 = _read_need(ue, 'Need0', 'LowValue', None)
            a1 = _read_need(ue, 'Need1', 'HighValue', None)
            b0 = _read_need(ue, 'Need2', 'LowValue2', None)
            b1 = _read_need(ue, 'Need3', 'HighValue2', None)

            def _pair_values(x, y):
                # both missing -> 0
                if x is None and y is None:
                    return 0, 0
                # both present
                if x is not None and y is not None:
                    if x != y:
                        s = f"{min(x,y)}~{max(x,y)}"
                        return s, s
                    return x, y
                # only one present -> use that for both slots (keeps existing indexing)
                v = x if x is not None else y
                return v, v

            n0, n1 = _pair_values(a0, a1)
            n2, n3 = _pair_values(b0, b1)
            needs = [n0, n1, n2, n3]

            # テンプレート向けに、[0] を第1ペアの範囲文字列、[1] を第2ペアの範囲文字列
            def _format_range(x, y):
                # treat sentinel/missing as invalid
                def _valid(v):
                    if v is None:
                        return False
                    try:
                        vi = int(v)
                    except Exception:
                        return True
                    if vi == 0 or vi == 65535:
                        return False
                    return True

                x_valid = _valid(x)
                y_valid = _valid(y)
                if not x_valid and not y_valid:
                    return ''
                try:
                    xi = int(x) if x_valid else None
                    yi = int(y) if y_valid else None
                except Exception:
                    xi = x; yi = y
                if xi is not None and yi is not None:
                    if xi == yi:
                        return f"{xi}"
                    mn, mx = min(xi, yi), max(xi, yi)
                    return f"{mn}~{mx}"
                # only one present
                return str(xi if xi is not None else yi)

            range1 = _format_range(a0, a1)
            range2 = _format_range(b0, b1)

            # 特殊ケース: 第1ペアが無く、第2ペアのみ存在する場合は
            # テンプレの [0] に第2ペアを割り当てる（第2ペアはそのまま [1] でも使える）
            if (not range1) and range2:
                range1 = range2

            # 基本の置換を行う。テンプレートの [0]/[1] が第1/第2ペアの範囲を参照するように渡す
            # tpl_values layout: [第1ペア範囲またはLow, 第1ペアHigh (n1), 第2ペア範囲, 第2ペアHigh(n3)]
            tpl_values = [range1, n1, range2, n3]
            final_text = replace_placeholders(tmpl, tpl_values)

            # 特殊例2のフォールバック処理：テンプレにプレースホルダがあり、置換後に
            # 数字が含まれない（＝データ無し）場合について処理する。
            if re.search(r'\[[+-]?\d+\]', tmpl) and not re.search(r'\d', final_text or ''):
                # まず、第1エフェクトの "1番目の値" をフォールバック候補として取得する
                fallback = None
                try:
                    first_ue = uefs[0]
                    cand = _read_need(first_ue, 'Need0', 'LowValue', None)
                    # 有効判定（従来ロジックに合わせる）
                    if cand is not None:
                        try:
                            ci = int(cand)
                            if ci != 0 and ci != 65535:
                                fallback = str(ci)
                        except Exception:
                            # 文字列等はそのまま使う
                            fallback = str(cand)
                except Exception:
                    fallback = None

                # フォールバックがある場合、tpl_values の空スロットを埋めて再置換する
                if fallback is not None and idx > 0:
                    new_vals = []
                    for v in tpl_values:
                        if v is None or (isinstance(v, str) and v.strip() == ''):
                            new_vals.append(fallback)
                        else:
                            new_vals.append(v)
                    tpl_values = new_vals
                    final_text = replace_placeholders(tmpl, tpl_values)

                # それでもデータがなければ明示的マーカー 'nullpo' を入れて再置換（検索用）
                if not re.search(r'\d', final_text or ''):
                    new_vals = []
                    for v in tpl_values:
                        if v is None or (isinstance(v, str) and v.strip() == ''):
                            new_vals.append('nullpo')
                        else:
                            new_vals.append(v)
                    tpl_values = new_vals
                    final_text = replace_placeholders(tmpl, tpl_values)

            # テンプレートにプレースホルダが無ければ、データがあるか確認して末尾に付加する
            if not re.search(r'\[[+-]?\d+\]', tmpl):
                def _valid_num(v):
                    try:
                        if isinstance(v, (int, float)):
                            return v != 0 and v != 65535
                        if isinstance(v, str) and v.isdigit():
                            iv = int(v)
                            return iv != 0 and iv != 65535
                    except Exception:
                        pass
                    return False

                def _make_suffix_from_pair(x, y):
                    # 両方無効/ゼロなら None
                    if not _valid_num(x) and not _valid_num(y):
                        return None
                    # 両方数値に変換できればレンジ/単一判定
                    try:
                        xi = int(x)
                        yi = int(y)
                        if xi == yi:
                            return f'[{xi}]'
                        mn, mx = min(xi, yi), max(xi, yi)
                        return f'[{mn}~{mx}]'
                    except Exception:
                        # 文字列でレンジ表記が既にある場合など
                        try:
                            sx = str(x)
                            if '~' in sx and any(ch.isdigit() for ch in sx):
                                return f'[{sx}]'
                        except Exception:
                            pass
                    return None

                suffix = _make_suffix_from_pair(n0, n1) or _make_suffix_from_pair(n2, n3)
                if suffix:
                    final_text = f"{final_text} {suffix}"

            ue_texts.append(final_text)
        if ue_texts:
            entry['unique_effects_text'] = ue_texts

        # unique_ops -> use group 175
        uops = item.get('unique_ops') or []
        uop_texts = []
        for uo in uops:
            eff = uo.get('EffectID')
            if eff is None or eff == 65535:
                continue
            tmpl = None
            tmpl = g175.get(str(eff)) if isinstance(g175, dict) else None
            if not tmpl:
                tmpl = g175.get(eff) if isinstance(g175, dict) else None
            if not tmpl:
                continue
            vals = uo.get('Values') or []
            uop_texts.append(replace_placeholders(tmpl, vals))
        if uop_texts:
            entry['unique_ops_text'] = uop_texts

        out[id_str] = entry

    return out


def select_file(var_label):
    path = filedialog.askopenfilename(title=f"Select {var_label}", filetypes=[("JSON files","*.json"), ("All files","*")])
    return path


def run_gui():
    root = tk.Tk()
    root.title('RSP Tooltip Generator')
    root.geometry('720x150')
    root.resizable(True, False)
    # allow column 1 (entries) to expand when resizing
    root.grid_columnconfigure(1, weight=1)

    item_path_var = tk.StringVar()
    text_path_var = tk.StringVar()

    def choose_item():
        p = select_file('Item JSON')
        if p:
            item_path_var.set(p)

    def choose_text():
        p = select_file('TextData JSON')
        if p:
            text_path_var.set(p)

    def execute():
        item_p = item_path_var.get()
        text_p = text_path_var.get()
        if not item_p or not text_p:
            messagebox.showerror('エラー', '両方のJSONファイルを選択してください')
            return
        try:
            with open(text_p, 'r', encoding='utf-8') as f:
                textdata = json.load(f)
            with open(item_p, 'r', encoding='utf-8') as f:
                itemdata = json.load(f)
        except Exception as e:
            messagebox.showerror('エラー', f'ファイル読み込み失敗: {e}')
            return

        out = process(itemdata, textdata)

        out_dir = Path(item_p).parent
        out_file = out_dir / 'rsp_item.json'
        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            messagebox.showinfo('完了', f'出力: {out_file}')
        except Exception as e:
            messagebox.showerror('エラー', f'出力失敗: {e}')

    # UI
    tk.Label(root, text='1) アイテムデータJSON').grid(row=0, column=0, sticky='w', padx=8, pady=6)
    tk.Entry(root, textvariable=item_path_var, width=80).grid(row=0, column=1, padx=4, sticky='we')
    tk.Button(root, text='選択', command=choose_item).grid(row=0, column=2, padx=4)

    tk.Label(root, text='2) テキストデータJSON').grid(row=1, column=0, sticky='w', padx=8, pady=6)
    tk.Entry(root, textvariable=text_path_var, width=80).grid(row=1, column=1, padx=4, sticky='we')
    tk.Button(root, text='選択', command=choose_text).grid(row=1, column=2, padx=4)

    tk.Button(root, text='実行', width=20, command=execute).grid(row=2, column=1, pady=12)

    root.mainloop()


if __name__ == '__main__':
    run_gui()
