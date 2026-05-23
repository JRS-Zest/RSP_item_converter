import struct
import json
import tkinter as tk
from tkinter import filedialog


# 確定した職業順序 (0:男 / 1:女) - モジュールレベルで定義して再利用
JOB_DATA = [
    ("剣士", 0), ("戦士", 0), ("ウィザード", 0), ("ウルフマン", 0),
    ("ビショップ", 0), ("天使", 0), ("シーフ", 0), ("武道家", 0),
    ("ランサー", 1), ("アーチャー", 1), ("ビーストテイマー", 1), ("サマナー", 1),
    ("プリンセス", 1), ("リトルウィッチ", 1), ("ネクロマンサー", 1),
    ("悪魔", 1), ("霊術師", 1), ("闘士", 1), ("光奏師", 0)
]

# 終端マーカーの2パターン
END_MARKER_A = b'\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF'
END_MARKER_B = b'\x01\x00\x00\x00\x00\x00\x00\x00\xFF\xFF'

def extract_from_path(file_path: str):
    """Extract items from the given decrypted item dat file and return a dict.

    This is a non-GUI API suitable for batch processing. It mirrors the
    behavior of the original interactive `extract_item_dat()`.
    """
    output = {}
    with open(file_path, "rb") as f:
        f.seek(12)
        while True:
            pos = f.tell()
            marker = f.read(6)
            if not marker or marker == b'\x7F\x02\x00\x00\x00\x00':
                break

            f.seek(pos)
            block = f.read(426)
            if len(block) < 426:
                break

            type_id = struct.unpack("<I", block[76:80])[0]

            # --- 基本ステータス (0B - 149B) ---
            fields = {
                "Index": struct.unpack("<I", block[0:4])[0],
                "Name": block[4:68].split(b'\x00')[0].decode('cp932', errors='ignore').strip(),
                "Unknown_68_72": block[68:72].hex(),
                "Unknown_72_76": block[72:76].hex(),
                "Type": type_id,
                "Unknown_80_96": block[80:96].hex(),
                "BasePrice": struct.unpack("<I", block[96:100])[0],
                "SellingType": struct.unpack("<H", block[100:102])[0],
                "AttackRange": struct.unpack("<H", block[102:104])[0],
                "Unknown_104_106": block[104:106].hex(),
                "AttackSpeed_raw": struct.unpack("<H", block[106:108])[0],
                "LowAP": struct.unpack("<H", block[110:112])[0] if type_id == 0 else struct.unpack("<H", block[108:110])[0],
                "HighAP": struct.unpack("<H", block[108:110])[0] if type_id == 0 else struct.unpack("<H", block[110:112])[0],
                "Durable": struct.unpack("<H", block[112:114])[0],
                "Unknown_114_120": block[114:120].hex(),
                "RequiredLevel": struct.unpack("<H", block[120:122])[0],
                "RequiredStatus": list(struct.unpack("<7H", block[122:136])),
                "Shape": struct.unpack("<H", block[136:138])[0],
                "ImageShapesIndex": struct.unpack("<H", block[138:140])[0],
                "Unknown_140_142": block[140:142].hex(),
                "QuestInfo": struct.unpack("<I", block[142:146])[0],
                "StackableNum": struct.unpack("<H", block[146:148])[0],
                "DropLevel": struct.unpack("<H", block[148:150])[0]
            }

            # --- Effect 抽出（10バイト単位） ---
            effects = []
            effect_base = 150
            max_effect_bytes = 48

            i = 0
            while i < (max_effect_bytes // 10):
                offset = effect_base + (i * 10)
                chunk = block[offset:offset+10]

                if len(chunk) < 10:
                    break

                # 終端マーカー判定
                if chunk == END_MARKER_A or chunk == END_MARKER_B:
                    break

                # 10バイト構造の読み取り
                l_val = struct.unpack('<H', chunk[0:2])[0]
                h_val = struct.unpack('<H', chunk[2:4])[0]
                l_val2 = struct.unpack('<H', chunk[4:6])[0]
                h_val2 = struct.unpack('<H', chunk[6:8])[0]
                effect_id = struct.unpack('<H', chunk[8:10])[0]

                # 特殊パターンチェック: 次のブロックを先読み
                if i + 1 < (max_effect_bytes // 10):
                    next_offset = effect_base + ((i + 1) * 10)
                    next_chunk = block[next_offset:next_offset+10]

                    if len(next_chunk) == 10:
                        next_l_val = struct.unpack('<H', next_chunk[0:2])[0]
                        next_h_val = struct.unpack('<H', next_chunk[2:4])[0]
                        next_l_val2 = struct.unpack('<H', next_chunk[4:6])[0]
                        next_h_val2 = struct.unpack('<H', next_chunk[6:8])[0]
                        next_effect_id = struct.unpack('<H', next_chunk[8:10])[0]

                        # 特殊パターン: 次のブロックのIDが0xFFFFでなく、かつNeedが全て0
                        if (next_effect_id != 0xFFFF and 
                            next_l_val == 0 and next_h_val == 0 and 
                            next_l_val2 == 0 and next_h_val2 == 0):

                            # 1番目のブロックから2つのEffectを抽出
                            effects.append({
                                "LowValue": l_val,
                                "HighValue": h_val,
                                "LowValue2": 0,
                                "HighValue2": 0,
                                "EffectID": effect_id
                            })

                            effects.append({
                                "LowValue": l_val2,
                                "HighValue": h_val2,
                                "LowValue2": 0,
                                "HighValue2": 0,
                                "EffectID": next_effect_id
                            })

                            # 2つのブロックを処理したのでスキップ
                            i += 2
                            continue

                # 通常パターン: 10バイト全てが0ならスキップ
                if effect_id == 0 and l_val == 0 and h_val == 0 and l_val2 == 0 and h_val2 == 0:
                    i += 1
                    continue

                effects.append({
                    "LowValue": l_val,
                    "HighValue": h_val,
                    "LowValue2": l_val2,
                    "HighValue2": h_val2,
                    "EffectID": effect_id
                })

                i += 1

            # --- Unique Option 6枠 (198B - 305B) ---
            ops = []
            for i in range(6):
                base = 198 + (i * 18)
                ops.append({
                    "EffectID": struct.unpack("<H", block[base:base+2])[0],
                    "Values": list(struct.unpack("<8H", block[base+2:base+18]))
                })

            # --- 追加解析セクション (288B - 425B) ---
            unknown_288_330 = block[288:330].hex()
            drop_coefficient = struct.unpack("<H", block[330:332])[0]
            unknown_332_356 = block[332:356].hex()

            # 性別・職業制限 (356B - )
            gender_byte = block[356]
            is_female_able = bool(gender_byte & 0x20)
            is_male_able = bool(gender_byte & 0x10)

            job_area = block[358:362]
            temp_enabled_jobs = []
            job_bit_count = 0
            
            for i, (name, gender) in enumerate(JOB_DATA):
                byte_idx = i // 8
                bit_idx = i % 8
                if job_area[byte_idx] & (1 << bit_idx):
                    job_bit_count += 1
                    if (gender == 0 and is_male_able) or (gender == 1 and is_female_able):
                        temp_enabled_jobs.append(name)

            # 要件メッセージの生成
            res_str = ""
            if job_bit_count == len(JOB_DATA):
                if is_male_able and not is_female_able:
                    res_str = "男性キャラ専用アイテム"
                elif is_female_able and not is_male_able:
                    res_str = "女性キャラ専用アイテム"
                else:
                    res_str = ""
            else:
                res_str = ", ".join(temp_enabled_jobs)

            # JSON構造の組み立て
            output[str(fields["Index"])] = {
                "fields": fields,
                "unique_effects": effects,
                "unique_ops": ops,
                "extended_data": {
                    "Unknown_288_330": unknown_288_330,
                    "DropCoefficient": drop_coefficient,
                    "Unknown_332_356": unknown_332_356
                },
                "requirements": res_str
            }

    return output


def extract_from_bytes(data: bytes) -> dict:
    """復号済みバイト列（ヘッダなし、426バイト×N）からアイテムを抽出する。

    extract_from_path はファイル先頭12バイトをスキップするため、
    12バイトのダミーヘッダを前置してから呼び出す。
    """
    import tempfile
    import os
    padded = b'\x00' * 12 + data
    with tempfile.NamedTemporaryFile(suffix='.dec.dat', delete=False) as tmp:
        tmp.write(padded)
        tmp_path = tmp.name
    try:
        return extract_from_path(tmp_path)
    finally:
        os.unlink(tmp_path)


def extract_item_dat():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="復号済みitem.datを選択してください")
    if not file_path:
        return

    output = extract_from_path(file_path)

    save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print("特殊パターン対応のEffect抽出が完了しました。")


if __name__ == "__main__":
    extract_item_dat()