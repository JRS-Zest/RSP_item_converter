#!/usr/bin/env python3
"""RSP アイテム一括生成ツール

item.dat + textData.dat を読み込み、RSPitem_{バージョン}.html を一発生成する。

パイプライン:
  item.dat (暗号化) → 復号 → JSON抽出 → ツールチップ生成 → レンダリング
  textData.dat (平文) → テキストデータ抽出
  → HTML テンプレートに埋め込み → RSPitem_{ver:04d}.html
"""

import importlib.util
import json
import os
import re
import struct
import sys
import tempfile
import threading
import tkinter as tk
import winreg
from collections import OrderedDict
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

# ─── PacketCrypt (PacketCrypt.cs の Python 移植) ──────────────────────────────
# aucDataTable: 440 bytes
_AUC = bytes([
    0xAF, 0x7E, 0xF5, 0xE7, 0xDD, 0xF9, 0xBE, 0xEE, 0xED, 0xBE, 0xCF, 0xBE, 0x9F, 0xBB, 0x7B, 0xE7,
    0xE7, 0x5F, 0xF5, 0xEE, 0xF5, 0xEE, 0xBE, 0xF6, 0xED, 0xFA, 0x77, 0x3F, 0xE7, 0x9F, 0xEB, 0x3F,
    0xF3, 0xF3, 0xDE, 0xF3, 0x77, 0xDD, 0xF3, 0xE7, 0x7E, 0xEE, 0xED, 0xDD, 0xE7, 0xF5, 0x3F, 0xEB,
    0x3F, 0x3F, 0x7D, 0x77, 0xFA, 0xD7, 0xEB, 0xED, 0xEE, 0xE7, 0x7E, 0xAF, 0x9F, 0xBB, 0xF3, 0xFC,
    0xDE, 0xDE, 0xBE, 0xDE, 0x7E, 0xF9, 0x9F, 0xF5, 0xBD, 0xFC, 0x7D, 0xF9, 0xDE, 0xBD, 0xDB, 0xDE,
    0x6F, 0xFC, 0xE7, 0xAF, 0xBD, 0x5F, 0x7D, 0x6F, 0x7B, 0x77, 0xBD, 0xF6, 0xDB, 0xAF, 0xF6, 0xB7,
    0x6F, 0xB7, 0xBB, 0xCF, 0x9F, 0x5F, 0xF5, 0x7D, 0xFA, 0x7E, 0x7B, 0xE7, 0xF5, 0xDD, 0x5F, 0xCF,
    0x77, 0xEB, 0xDE, 0xF5, 0x5F, 0x6F, 0x77, 0x9F, 0xAF, 0xEE, 0x7B, 0x6F, 0xCF, 0xDD, 0xDD, 0xBE,
    0xFA, 0x9F, 0xCF, 0x7D, 0xCF, 0xBE, 0x7B, 0xFC, 0xF5, 0xDB, 0xDE, 0xE7, 0xEE, 0xF9, 0xF9, 0xDD,
    0xF3, 0xDE, 0xF5, 0xCF, 0x6F, 0xCF, 0xDB, 0xBB, 0xFA, 0xFC, 0xF9, 0xF6, 0xE7, 0xDB, 0xFC, 0xF3,
    0xB7, 0xCF, 0x6F, 0xDD, 0xD7, 0xF9, 0xBB, 0x7D, 0xBD, 0xDD, 0x3F, 0x5F, 0xDE, 0xF6, 0x7E, 0xE7,
    0xFA, 0xBE, 0xCF, 0xE7, 0xAF, 0xFA, 0xBE, 0xFA, 0xEB, 0xBE, 0xAF, 0xE7, 0xBE, 0xDE, 0xF9, 0x3F,
    0xF3, 0x6F, 0xCF, 0x6F, 0xB7, 0xB7, 0xEE, 0xF6, 0xCF, 0xF3, 0x9F, 0xDB, 0x7B, 0xD7, 0xEB, 0xED,
    0x3F, 0xED, 0xF3, 0x77, 0xAF, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x48, 0x00, 0x00, 0x00,
    0xD4, 0x5A, 0xAE, 0x3F, 0x04, 0x00, 0x00, 0x00, 0x6F, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00,
    0x49, 0x00, 0x00, 0x00, 0x45, 0x00, 0x00, 0x00, 0xFD, 0xFE, 0x00, 0x00, 0x09, 0x00, 0x00, 0x00,
    0x08, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x00, 0x7B, 0x7D, 0xB7, 0xBD,
    0xAF, 0xBB, 0x3F, 0x7D, 0xDB, 0xAF, 0xEE, 0xB7, 0x7E, 0x7E, 0xF6, 0x77, 0x77, 0xBB, 0xE7, 0x77,
    0x9F, 0x7B, 0xF6, 0x7D, 0xF5, 0xF5, 0x6F, 0x5F, 0xED, 0x7E, 0xDE, 0xF3, 0xF5, 0xF5, 0x9F, 0xDE,
    0xF3, 0xFC, 0xEB, 0xF9, 0x5F, 0xAF, 0xF3, 0xD7, 0xFA, 0xDD, 0x5F, 0xBB, 0xEB, 0xE7, 0xD7, 0xD7,
    0xF3, 0xD7, 0x7B, 0x7D, 0xF5, 0xEB, 0xBB, 0xF5, 0x7E, 0xDD, 0xFA, 0xCF, 0xED, 0xFA, 0xFA, 0xF6,
    0xEE, 0xF6, 0x6F, 0x00, 0x7B, 0x7D, 0xB7, 0xBD, 0xAF, 0xBB, 0x3F, 0x7D, 0xDB, 0xAF, 0xEE, 0xB7,
    0x7E, 0x7E, 0xF6, 0x77, 0x77, 0xBB, 0xE7, 0x77, 0x9F, 0x7B, 0xF6, 0x7D, 0xF5, 0xF5, 0x6F, 0x5F,
    0xED, 0x7E, 0xDE, 0xF3, 0xF5, 0xF5, 0x9F, 0xDE, 0xF3, 0xFC, 0xEB, 0xF9, 0x5F, 0xAF, 0xF3, 0xD7,
    0xFA, 0xDD, 0x5F, 0xBB, 0xEB, 0xE7, 0xD7, 0xD7, 0xF3, 0xD7, 0x7B, 0x7D, 0xF5, 0xEB, 0xBB, 0xF5,
    0x7E, 0xDD, 0xFA, 0xCF, 0xED, 0xFA, 0xFA, 0xF6, 0xEE, 0xF6, 0x6F, 0x00, 0xD0, 0xC0, 0x7C, 0x00,
    0xC0, 0xC0, 0x7C, 0x00, 0xB4, 0xC0, 0x7C, 0x00, 0xA8, 0xC0, 0x7C, 0x00, 0xA0, 0xC0, 0x7C, 0x00,
    0x98, 0xC0, 0x7C, 0x00, 0xA0, 0x31, 0x7D, 0x00,
])  # 440 bytes

# xorKeys: 213 bytes (先頭71バイトは 0x00)
_XOR = bytes([
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x5F, 0xB7, 0x7D, 0xE7, 0xCF, 0xFA, 0x5F, 0xDB,
    0xCF, 0xAF, 0xDD, 0x7E, 0xEB, 0xEE, 0xED, 0x7E, 0xDE, 0x77, 0xCF, 0x7E, 0xD7, 0xEE, 0xB7, 0xBD,
    0x6F, 0x9F, 0x7D, 0xBE, 0xE7, 0xED, 0x6F, 0xDD, 0xED, 0xDB, 0xF3, 0xDB, 0xAF, 0x3F, 0xDB, 0xEE,
    0xD7, 0x7D, 0xDD, 0x6F, 0x9F, 0x6F, 0xAF, 0x7E, 0x5F, 0x3F, 0x7E, 0xFA, 0x77, 0xBE, 0xFA, 0x9F,
    0xE7, 0xE7, 0xBB, 0xDD, 0xDD, 0xED, 0xE7, 0xEE, 0x9F, 0x7B, 0xEE, 0xAF, 0x5F, 0xAF, 0xBD, 0xBB,
    0x7E, 0x6F, 0x7D, 0xCF, 0xF3, 0x9F, 0x9F, 0xB7, 0xDD, 0xD7, 0xED, 0x7D, 0xBB, 0xDB, 0xBB, 0xDB,
    0x9F, 0xED, 0xBB, 0xBB, 0xEB, 0xDE, 0xAF, 0xDB, 0x5F, 0xFA, 0x6F, 0xB7, 0xCF, 0xBE, 0xDE, 0xAF,
    0xB7, 0xDD, 0xB7, 0xAF, 0x6F, 0xDE, 0xEB, 0xE7, 0x6F, 0x3F, 0xF3, 0xFA, 0xF3, 0xBB, 0xFC, 0x7E,
    0xDD, 0x7E, 0xE7, 0x7E, 0xB7, 0xBE, 0xEE, 0xFA, 0xF9, 0xB7, 0x5F, 0x7B, 0xED, 0x3F, 0x7B, 0x6F,
    0xB7, 0xD7, 0x6F, 0xFC, 0x9F,
])  # 213 bytes


def _gen_decode_key(raw_key: int) -> int:
    """GenerateScenarioDecodeKey の Python 移植。"""
    if raw_key == -1:
        return 0
    return 2 - (0 if raw_key == 1 else 1)


def _decode(data: bytes, decode_key: int) -> bytes:
    """DecodeScenarioBuffer の Python 移植。"""
    result = bytearray(len(data))
    auc_len = len(_AUC)
    xor_len = len(_XOR)
    table_offset = (decode_key * 9 << 3) - decode_key
    enc = 0
    for i, b in enumerate(data):
        idx = enc + table_offset
        en = (_AUC[idx % auc_len] + _XOR[idx % xor_len]) & 0xFF
        result[i] = b ^ en
        enc += 1
        if enc >= 0x47:
            enc = 0
    return bytes(result)


# ─── item.dat 復号 ────────────────────────────────────────────────────────────

def decrypt_item_dat(path: str):
    """item.dat を復号してアイテムバイト列とアイテム数を返す。

    item.dat のバイナリ構造:
      [0:4]  rawKey (int32, 平文)
      [4:8]  itemCount (int32, 暗号化)
      [8:12] unknown (uint32, 平文)
      [12:]  items (426バイト×N, 暗号化)
    """
    with open(path, 'rb') as f:
        data = f.read()
    raw_key = struct.unpack_from('<i', data, 0)[0]
    dk = _gen_decode_key(raw_key)
    item_count = struct.unpack_from('<i', _decode(data[4:8], dk), 0)[0]
    if item_count <= 0 or item_count > 100000:
        raise ValueError(f'アイテム数が異常です: {item_count}。item.dat のフォーマットを確認してください。')
    items_bytes = _decode(data[12:12 + item_count * 426], dk)
    return items_bytes, item_count


# ─── textData.dat パース ──────────────────────────────────────────────────────

def parse_textdata_dat(path: str) -> dict:
    """textData.dat をバイナリ解析して textdata dict を返す。

    TesxDatから抽出json.py のロジックをGUIなしで関数化したもの。
    戻り値: {"357": {id: text, ...}, "175": {...}, "29": {...}}
    """
    with open(path, 'rb') as f:
        content = f.read()

    # マーカーパターン: (pattern, group_id, マーカー後のデータ開始オフセット)
    search_targets = [
        (b'\x65\x01\x00\x00\x00\x00\x00\x00', '357', 4),
        (b'\x00\x00\xAF\x00\x00\x00\x00\x00\x00\x00', '175', 6),
        (b'\x1D\x00\x00\x00\x00\x00\x00\x00', '29', 4),
    ]

    found_markers = []
    for pattern, gid, skip in search_targets:
        pos = 0
        max_pos = -1
        while True:
            pos = content.find(pattern, pos)
            if pos == -1:
                break
            max_pos = pos
            pos += len(pattern)
        if max_pos >= 0:
            found_markers.append({'id': gid, 'offset': max_pos, 'skip': skip})

    found_markers.sort(key=lambda x: x['offset'])

    results = OrderedDict()
    block_size = 260
    for i, m in enumerate(found_markers):
        gid = m['id']
        ptr = m['offset'] + m['skip']
        end = found_markers[i + 1]['offset'] if i + 1 < len(found_markers) else len(content)
        results[gid] = OrderedDict()
        while ptr < end:
            remaining = end - ptr
            if remaining < 4:
                break
            block = content[ptr:ptr + min(block_size, remaining)]
            data_id = struct.unpack('<I', block[:4])[0]
            null_pos = block[4:].find(b'\x00')
            raw = block[4:4 + null_pos] if null_pos != -1 else block[4:]
            try:
                text = raw.decode('shift_jis', errors='replace')
                text = re.sub(r'<c:\w+>', '', text).replace('<n>', '')
            except Exception:
                text = ''
            results[gid][str(data_id)] = text
            ptr += block_size

    return results


# ─── レジストリ読み込み ───────────────────────────────────────────────────────

_REG_KEY = r'Software\L&K Logic Korea\Red Stone Portable for Japan'


def read_game_registry():
    """(version: int|None, install_path: str|None) を返す。

    Windows レジストリ (HKEY_CURRENT_USER) を winreg で直接読む。
    常に最新のインストール済みバージョンを返す。
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as key:
            version, _    = winreg.QueryValueEx(key, 'Version')
            install_path, _ = winreg.QueryValueEx(key, 'path')
        return int(version), str(install_path)
    except Exception:
        return None, None


# ─── HTML 生成 ────────────────────────────────────────────────────────────────

_PLACEHOLDER = 'const rawData = ★★★★ここにデータを貼り付ける★★★★;'


def _resource_base() -> Path:
    """PyInstaller frozen 時は sys._MEIPASS、通常時はスクリプト親フォルダを返す。"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def _template_path() -> Path:
    base = _resource_base()
    if getattr(sys, 'frozen', False):
        return base / 'アイテム表示用HTMLベース.html'
    return base.parent / 'アイテムオプションデータ保管' / 'アイテム表示用HTMLベース.html'


def build_html(rendered: dict) -> str:
    """HTMLテンプレートにレンダリング済み dict を埋め込んで HTML 文字列を返す。"""
    tpath = _template_path()
    if not tpath.exists():
        raise FileNotFoundError(f'HTMLテンプレートが見つかりません:\n{tpath}')
    template = tpath.read_text(encoding='utf-8')
    json_str = json.dumps(rendered, ensure_ascii=False)
    return template.replace(_PLACEHOLDER, f'const rawData = {json_str};')


# ─── パイプライン ─────────────────────────────────────────────────────────────

def _load_mod(rel_path: str, name: str):
    """開発時はスクリプトフォルダ、EXE時は sys._MEIPASS からモジュールをロードする。"""
    path = _resource_base() / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_pipeline(item_dat_path: str, textdata_dat_path: str, log_fn) -> dict:
    """全ステップを実行してレンダリング済み dict を返す。"""
    log_fn('▶ item.dat を復号中...')
    dec_bytes, item_count = decrypt_item_dat(item_dat_path)
    log_fn(f'  {item_count} アイテム 復号完了')

    log_fn('▶ アイテムデータを JSON に変換中...')
    ext_mod = _load_mod('複合itemdatからjson抽出.py', 'ext_mod')
    items = ext_mod.extract_from_bytes(dec_bytes)
    log_fn(f'  {len(items)} アイテム 抽出完了')

    log_fn('▶ textData.dat をパース中...')
    textdata = parse_textdata_dat(textdata_dat_path)
    log_fn(f'  グループ {list(textdata.keys())} 取得完了')

    log_fn('▶ ツールチップを生成中...')
    tip_mod = _load_mod('rsp_tooltip_generator.py', 'tip_mod')
    rsp_items = tip_mod.process(items, textdata)
    log_fn(f'  {len(rsp_items)} アイテム 完了')

    log_fn('▶ レンダリング中...')
    rend_mod = _load_mod('render_rsp_items.py', 'rend_mod')
    rendered = {}
    for k in sorted(rsp_items.keys(), key=lambda x: int(x)):
        rendered[k] = rend_mod.make_entry(rsp_items[k], textdata)
    log_fn(f'  {len(rendered)} アイテム レンダリング完了')

    return rendered


# ─── GUI ──────────────────────────────────────────────────────────────────────

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('RSP アイテム一括生成')
        root.resizable(True, False)

        # レジストリから初期値を取得
        version, install_path = read_game_registry()
        self.version = version
        base = install_path or r'C:\Program Files (x86)\GameON\RED STONE Portable'
        ver_str = f'{version:04d}' if version is not None else '取得失敗'

        default_item = str(Path(base) / 'Data' / 'Scenario' / 'Red Stone' / 'item.dat')
        default_text = str(Path(base) / 'Data' / 'textData.dat')
        # 出力フォルダのデフォルト: EXE自身と同じフォルダ
        if getattr(sys, 'frozen', False):
            default_out = str(Path(sys.executable).parent)
        else:
            default_out = str(Path(__file__).parent)

        pad = dict(padx=10, pady=3)

        # バージョン・パス表示
        tk.Label(
            root,
            text=f'検出バージョン: {ver_str}    インストール先: {base}',
            anchor='w', fg='#555', font=('', 9),
        ).grid(row=0, column=0, columnspan=3, sticky='we', **pad)

        # ファイル選択行
        self.item_path = self._file_row(root, 1, 'item.dat', default_item, '*.dat')
        self.text_path = self._file_row(root, 3, 'textData.dat', default_text, '*.dat')
        self.out_path  = self._dir_row (root, 5, '出力フォルダ', default_out)

        # ログ
        self.log_box = scrolledtext.ScrolledText(
            root, width=80, height=14, state='disabled', font=('Courier New', 9)
        )
        self.log_box.grid(row=7, column=0, columnspan=3, padx=10, pady=4, sticky='we')

        # 実行ボタン
        self.btn_run = tk.Button(
            root, text='生成実行', command=self._on_run,
            bg='#4A90E2', fg='white', font=('', 11, 'bold'), width=20, pady=4,
        )
        self.btn_run.grid(row=8, column=0, columnspan=3, pady=8)

        root.columnconfigure(0, weight=1)

    # ── ウィジェット helper ─────────────────────────────────────────────────

    def _file_row(self, parent, row, label, default, ext):
        tk.Label(parent, text=label, anchor='w').grid(
            row=row, column=0, sticky='w', padx=10)
        var = tk.StringVar(value=default)
        tk.Entry(parent, textvariable=var, width=62).grid(
            row=row + 1, column=0, columnspan=2, padx=10, sticky='we')
        tk.Button(parent, text='選択',
                  command=lambda v=var, e=ext: self._pick_file(v, e)).grid(
            row=row + 1, column=2, padx=4)
        return var

    def _dir_row(self, parent, row, label, default):
        tk.Label(parent, text=label, anchor='w').grid(
            row=row, column=0, sticky='w', padx=10)
        var = tk.StringVar(value=default)
        tk.Entry(parent, textvariable=var, width=62).grid(
            row=row + 1, column=0, columnspan=2, padx=10, sticky='we')
        tk.Button(parent, text='選択',
                  command=lambda v=var: self._pick_dir(v)).grid(
            row=row + 1, column=2, padx=4)
        return var

    def _pick_file(self, var, ext):
        p = Path(var.get())
        init = str(p.parent) if p.parent.exists() else str(Path.home())
        f = filedialog.askopenfilename(
            initialdir=init,
            filetypes=[('DAT ファイル', ext), ('すべてのファイル', '*.*')],
        )
        if f:
            var.set(f)

    def _pick_dir(self, var):
        p = Path(var.get())
        init = str(p) if p.exists() else str(Path.home())
        d = filedialog.askdirectory(initialdir=init)
        if d:
            var.set(d)

    # ── ログ ───────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log_box.config(state='normal')
        self.log_box.insert('end', msg + '\n')
        self.log_box.see('end')
        self.log_box.config(state='disabled')
        self.root.update_idletasks()

    # ── 実行 ───────────────────────────────────────────────────────────────

    def _on_run(self):
        item_p = self.item_path.get().strip()
        text_p = self.text_path.get().strip()
        out_d  = self.out_path.get().strip()

        if not Path(item_p).exists():
            messagebox.showerror('エラー', f'item.dat が見つかりません:\n{item_p}')
            return
        if not Path(text_p).exists():
            messagebox.showerror('エラー', f'textData.dat が見つかりません:\n{text_p}')
            return
        if not _template_path().exists():
            messagebox.showerror('エラー', f'HTML テンプレートが見つかりません:\n{_template_path()}')
            return
        if not Path(out_d).exists():
            messagebox.showerror('エラー', f'出力フォルダが見つかりません:\n{out_d}')
            return

        # ログクリア
        self.log_box.config(state='normal')
        self.log_box.delete('1.0', 'end')
        self.log_box.config(state='disabled')

        # ボタン無効化して実行
        self.btn_run.config(state='disabled', text='実行中...')
        self.root.update_idletasks()

        def worker():
            try:
                rendered = run_pipeline(item_p, text_p, self._log)

                ver = self.version
                fname = f'RSPitem_{ver:04d}.html' if ver is not None else 'RSPitem_unknown.html'
                self._log(f'▶ HTML を生成中... → {fname}')
                html = build_html(rendered)
                out_path = Path(out_d) / fname
                out_path.write_text(html, encoding='utf-8')
                self._log(f'✔ 完了: {out_path}')
                self.root.after(0, lambda: messagebox.showinfo('完了', f'生成しました:\n{out_path}'))
            except Exception as e:
                import traceback
                self._log(f'✖ エラー: {e}')
                self._log(traceback.format_exc())
                err_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror('エラー', err_msg))
            finally:
                self.root.after(0, lambda: self.btn_run.config(state='normal', text='生成実行'))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
