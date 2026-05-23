import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# 入出力パス
ITEM_IN = Path(__file__).parent / '参考用ファイル' / 'rsp_item.json'
TEXT_IN = Path(__file__).parent / 'textdata_final_fix.json'
OUT = Path(__file__).parent / '参考用ファイル' / 'rsp_item2.json'

# 型別マップ（tooltip_spec から）
TYPE_MAP = {
    0: '帽子', 1: '冠', 2: 'グローブ', 3: '槍投', 4: 'クロー', 5: '手首', 6: 'ベルト', 7: '足',
    8: '首', 9: '指', 10: '耳', 11: '背中', 12: 'ブロ', 13: '腕刺青', 14: '肩刺青', 15: '十字架',
    16: '鎧', 17: '職鎧', 18: '片手剣', 19: '盾', 20: '両手剣', 21: '杖', 22: '牙', 23: '棍棒',
    24: '翼', 25: '短剣', 26: '弓', 27: '矢', 28: '槍', 29: '笛', 30: 'スリング', 31: 'ボトル',
    32: '棒', 33: '鞭', 34: '原石', 35: '赤POT', 36: '青POT', 37: '水薬', 38: '能力アップ', 39: '異常回復',
    40: '復活系', 41: '鍵', 42: '帰還', 43: '必殺技の巻物', 44: 'お菓子', 45: '霊薬', 46: '魔法液',
    47: 'セッティング原石', 48: 'その他特殊アイテム', 49: 'クエストアイテム', 50: '課金アイテム',
    51: 'エンチャント系', 52: 'ロト系', 54: '鎌', 55: '闘士武器', 56: '本'
}

REQ_LABELS = ['力', '敏捷', '健康', '知恵', '知識', 'カリスマ', '幸運']


def load_json(p: Path):
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def make_entry(item, textdata):
    out = []
    name = item.get('Name') or item.get('fields', {}).get('Name') or ''
    out.append(name)
    out.append('<基本情報>')

    # Type may be at top-level or under fields; normalize and map via TYPE_MAP
    t = item.get('Type')
    if t is None:
        t = (item.get('fields') or {}).get('Type')

    type_str = ''
    if isinstance(t, int):
        type_str = TYPE_MAP.get(t, str(t))
    elif isinstance(t, str):
        try:
            ti = int(t)
            type_str = TYPE_MAP.get(ti, t)
        except Exception:
            type_str = t
    else:
        type_str = str(t) if t is not None else ''

    out.append(f'- {type_str}')

    # unique effects (text already rendered keys) or build from dicts using textdata['357']
    uefs = item.get('unique_effects_text') or item.get('UniqueEffects') or item.get('unique_effects') or []

    # tooltip 側で既に整形された攻撃情報があればそのまま表示する
    atk_str = item.get('攻撃力')
    if atk_str:
        out.append(f'- 攻撃力 {atk_str}')
    # 射程は数値や文字列で入る想定
    range_val = item.get('射程')
    if range_val is not None:
        out.append(f'- 射程 {range_val}')
    if uefs:
        # if elements are dicts with EffectID, perform template replacement
        if any(isinstance(x, dict) for x in uefs):
            parent = (textdata or {}).get('357', {})
            for ue in uefs:
                if not isinstance(ue, dict):
                    s = str(ue)
                else:
                    eff_id = ue.get('EffectID') if ue.get('EffectID') is not None else ue.get('EffectId')
                    if eff_id is None:
                        s = str(ue)
                    else:
                        try:
                            if int(eff_id) == 65535:
                                continue
                        except Exception:
                            pass
                        template = parent.get(str(eff_id), '')
                        if not template:
                            s = str(ue)
                        else:
                            # Need0..Need3 replacement
                            vals = [ue.get(f'Need{i}') for i in range(4)]
                            t = template
                            # replace indexed placeholders [0].. and signed variants
                            for idx, v in enumerate(vals):
                                rep = '' if v is None else str(v)
                                t = t.replace(f'[+{idx}]', f'+{rep}' if rep != '' else '')
                                t = t.replace(f'[-{idx}]', f'-{rep}' if rep != '' else '')
                                t = t.replace(f'[{idx}]', rep)
                            s = t.replace('\r\n', '\n').replace('\n', ' ').strip()
                if not s:
                    continue
                if not s.startswith('- '):
                    s = f'- {s}'
                out.append(s)
        else:
            for ue in uefs:
                s = ue
                if not isinstance(s, str):
                    s = str(s)
                if not s.startswith('- '):
                    s = f'- {s}'
                out.append(s)

    # unique ops: build from dicts using textdata['175'] when needed
    uops = item.get('unique_ops_text') or item.get('UniqueOps') or item.get('unique_ops') or []
    if uops:
        if any(isinstance(x, dict) for x in uops):
            parent_ops = (textdata or {}).get('175', {})
            for uo in uops:
                if not isinstance(uo, dict):
                    s = str(uo)
                else:
                    eff_id = uo.get('EffectID') if uo.get('EffectID') is not None else uo.get('EffectId')
                    if eff_id is None:
                        s = str(uo)
                    else:
                        try:
                            if int(eff_id) == 65535:
                                continue
                        except Exception:
                            pass
                        template = parent_ops.get(str(eff_id), '')
                        if not template:
                            s = str(uo)
                        else:
                            vals = uo.get('Values') or uo.get('values') or []
                            t = template
                            for idx in range(len(vals)):
                                rep = '' if vals[idx] is None else str(vals[idx])
                                t = t.replace(f'[+{idx}]', f'+{rep}' if rep != '' else '')
                                t = t.replace(f'[-{idx}]', f'-{rep}' if rep != '' else '')
                                t = t.replace(f'[{idx}]', rep)
                            s = t.replace('\r\n', '\n').replace('\n', ' ').strip()
                if not s:
                    continue
                if not s.startswith('- '):
                    s = f'- {s}'
                out.append(s)
        else:
            for uo in uops:
                s = uo
                if not isinstance(s, str):
                    s = str(s)
                if not s.startswith('- '):
                    s = f'- {s}'
                out.append(s)

    out.append('<要求能力値>')
    # RequiredLevel: only output if present and non-zero
    if 'RequiredLevel' in item:
        lvl = item.get('RequiredLevel')
    else:
        lvl = (item.get('fields') or {}).get('RequiredLevel')
    try:
        lvl_val = int(lvl) if lvl is not None else 0
    except Exception:
        lvl_val = 0
    if lvl_val != 0:
        out.append(f'- レベル {lvl_val}')

    reqs = item.get('RequiredStatus') or (item.get('fields') or {}).get('RequiredStatus') or []
    # some sources store as list of numbers or list of strings
    if reqs and all(isinstance(x, int) for x in reqs):
        for label, val in zip(REQ_LABELS, reqs):
            if val:
                out.append(f'- {label} {val}')
    else:
        # assume already formatted strings
        for r in reqs:
            if isinstance(r, str) and r.strip():
                out.append(f'- {r}')

    out.append('<着用可能な職業>')
    reqstr = item.get('requirements') or item.get('requirements', '') or ''
    if isinstance(reqstr, str):
        if reqstr.strip():
            parts = [s.strip() for s in reqstr.split(',') if s.strip()]
            for p in parts:
                out.append(f'- {p}')
    elif isinstance(reqstr, list):
        for p in reqstr:
            out.append(f'- {p}')

    out.append('<DropLv/係数>')
    dlv = item.get('DropLevel') or (item.get('fields') or {}).get('DropLevel')
    if isinstance(dlv, int):
        out.append(f'- ドロップレベル {dlv}')
    elif isinstance(dlv, str) and dlv.startswith('-'):
        out.append(dlv)
    else:
        out.append(f'- ドロップレベル {dlv if dlv is not None else ""}')

    # DropCoefficient try multiple places
    dcoef = item.get('DropCoefficient') or (item.get('extended_data') or {}).get('DropCoefficient')
    if not dcoef:
        # fallback default 1000
        dcoef = 1000
    out.append(f'- ドロップ係数 {dcoef}')

    return out


def main():
    run_with_paths(ITEM_IN, TEXT_IN, OUT)


def run_with_paths(item_in_path, text_in_path, out_path):
    """Run processing using explicit paths (Path or str)."""
    item_in_path = Path(item_in_path)
    text_in_path = Path(text_in_path)
    out_path = Path(out_path)

    if not item_in_path.exists():
        print('入力ファイルが見つかりません:', item_in_path)
        return
    if not text_in_path.exists():
        print('テキストデータが見つかりません:', text_in_path)
        return

    if out_path.exists():
        print('出力ファイルが既に存在します（上書きします）:', out_path)

    items = load_json(item_in_path)
    textdata = load_json(text_in_path)

    rendered = {}
    for k in sorted(items.keys(), key=lambda x: int(x)):
        item = items[k]
        rendered[k] = make_entry(item, textdata)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(rendered, f, ensure_ascii=False, indent=2)

    print('出力完了:', out_path)


class App:
    def __init__(self, root):
        self.root = root
        root.title('Render RSP Items')

        self.item_path = tk.StringVar(value=str(ITEM_IN))
        self.text_path = tk.StringVar(value=str(TEXT_IN))
        self.out_path = tk.StringVar(value=str(OUT))

        tk.Label(root, text='入力アイテムファイル').grid(row=0, column=0, sticky='w')
        tk.Entry(root, textvariable=self.item_path, width=60).grid(row=1, column=0, columnspan=2)
        tk.Button(root, text='選択', command=self.select_item).grid(row=1, column=2)

        tk.Label(root, text='テキストデータファイル').grid(row=2, column=0, sticky='w')
        tk.Entry(root, textvariable=self.text_path, width=60).grid(row=3, column=0, columnspan=2)
        tk.Button(root, text='選択', command=self.select_text).grid(row=3, column=2)

        tk.Label(root, text='出力ファイル').grid(row=4, column=0, sticky='w')
        tk.Entry(root, textvariable=self.out_path, width=60).grid(row=5, column=0, columnspan=2)
        tk.Button(root, text='選択', command=self.select_out).grid(row=5, column=2)

        tk.Button(root, text='実行', command=self.run).grid(row=6, column=0)
        tk.Button(root, text='閉じる', command=root.quit).grid(row=6, column=1)

    def select_item(self):
        p = filedialog.askopenfilename(title='入力ファイルを選択', filetypes=[('JSON', '*.json'), ('All', '*.*')])
        if p:
            self.item_path.set(p)

    def select_text(self):
        p = filedialog.askopenfilename(title='テキストファイルを選択', filetypes=[('JSON', '*.json'), ('All', '*.*')])
        if p:
            self.text_path.set(p)

    def select_out(self):
        p = filedialog.asksaveasfilename(title='出力ファイルを選択', defaultextension='.json', filetypes=[('JSON', '*.json'), ('All', '*.*')])
        if p:
            self.out_path.set(p)

    def run(self):
        item_p = self.item_path.get()
        text_p = self.text_path.get()
        out_p = self.out_path.get()
        if not item_p or not text_p or not out_p:
            messagebox.showerror('エラー', '全てのパスを指定してください')
            return
        try:
            run_with_paths(item_p, text_p, out_p)
            messagebox.showinfo('完了', f'出力しました: {out_p}')
        except Exception as e:
            messagebox.showerror('エラー', str(e))


if __name__ == '__main__':
    # launch GUI so user can choose paths; keeps existing defaults prefilled
    root = tk.Tk()
    app = App(root)
    root.mainloop()
