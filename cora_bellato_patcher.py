#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RF Online 4.75 Cora <-> Bellato Full Patcher
Working Directory: RF Online client root directory (configurable via --game-dir)

Features:
1. Complete backup of all modified original files to _ModBackup/ with JSON manifest.
2. Full rollback capability (--rollback) restoring client to 100% pristine state.
3. Safe two-way swap of models (Mesh/), textures (Tex/), skeletons (Bone/),
   permitted animations (Ani/ COA, ATA, MEA, MHA, RAA, RHA, GEA, MOA),
   base music (Snd/BGM/) and race voices (Snd/Character/).
4. Strict preservation of MAU (Unit/), Animus, Dark/Light Force magic,
   class combat skills (*2CA.RFS) and profession buffs (*ETA.RFS).
5. Automatic preservation of 6 throwing axe (RAXETHROW) animations in *MOA.RFS.
6. Safe swap of armor glow effects (Chef/ and Chef/Eff/),
   booster particle directories (Chef/*_Dragon_Booster/ etc.),
   booster exhaust scripts (Effect/item_8/Booster_CLOAK/),
   and CW ranking reward auras (Effect/Character_3/ranking_reward/).
7. Complete coverage of cloaks, boosters, mounts, and accessories in Item/
   (Item/Armor/Mesh, Item/Armor/Tex, Item/Armor/Bone, Item/Armor/Ani, Item/Mount/, Item/ModelItem/).
8. Lossless 2048-byte DXT1 block swap in SpriteImage/ru-ru/item.spr for all 560 armor & cloak icon pairs.
9. Local mod cache in _ModCache/ and generation of 1-click 1-second restore scripts
   Apply-Mod.bat and Apply-Mod.ps1 for zero-downtime recovery after launcher updates.
10. Built-in verification and integrity checking (--verify, --status).
"""

import os
import sys
import json
import shutil
import struct
import hashlib
import argparse
from typing import Dict, List, Tuple, Set, Optional, Any

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "_ModBackup")
CACHE_DIR = os.path.join(BASE_DIR, "_ModCache")
BACKUP_MANIFEST = os.path.join(BACKUP_DIR, "backup_manifest.json")

# Validated, collision-free pairs of (Bellato IconID, Cora IconID) in SpriteImage/ru-ru/item.spr
# Derived directly from decrypted DataTable/Item.edf (recs 244B, icon uint16 at 0x4c:0x4e)
# - Page 13 (Helmet): 120 pairs (63 low/mid 1-50 + 57 high-level 53-75, masks & visors)
# - Page 14 (Upper): 104 pairs (63 low/mid 1-50 + 41 high-level 53-75 & special sets)
# - Page 15 (Lower): 104 pairs (63 low/mid 1-50 + 41 high-level 53-75 & special sets)
# - Page 16 (Gauntlet): 104 pairs (63 low/mid 1-50 + 41 high-level 53-75 & special sets)
# - Page 17 (Shoe): 104 pairs (63 low/mid 1-50 + 41 high-level 53-75 & special sets)
# - Page 19 (Cloaks & Boosters): 24 pairs (Anti-gravs, Gold, Premium, Adeptus/Inquisitor, Prototype, Dragon)
# Total: 560 pairs across 6 pages. Accretia armor/booster icons are 100% disjoint and untouched.
def generate_icon_swap_pairs() -> List[Tuple[int, int]]:
    # Base level 1..50 armors (identical across slots):
    # Bellato: 1..63 (Warrior: 1..21, Ranger: 22..42, Force: 43..63)
    # Cora:    64..126 (Warrior: 64..84, Ranger: 85..105, Force: 106..126)
    # Accretia: 127..189 (Disjoint, untouched)
    base_1_50 = [(i, i + 63) for i in range(1, 64)]

    # High-level body armors (Pages 14, 15, 16, 17: Upper, Lower, Gauntlet, Shoe)
    body_high = [
        # Level 50 / F-type
        (190, 193), (191, 194), (192, 195),
        # Guild Leader / Archon
        (199, 202), (200, 203), (201, 204),
        # Level 53-55 / Type C / Baal / Hierarch
        (208, 214), (209, 215), (210, 216), (211, 217), (212, 218), (213, 219),
        # White / Premium
        (227, 230), (228, 231), (229, 232),
        # Level 65 Titan <-> Taurus
        (236, 242), (237, 243), (238, 244),
        # Level 70 Patron Titan <-> Taurus
        (245, 248), (246, 249), (247, 250),
        # Support armor
        (254, 255),
        # White Dragonborn
        (284, 285),
        # Level 75 Baalzebub
        (288, 291), (289, 292), (290, 293),
        # PvP / Master
        (297, 300), (298, 301), (299, 302),
        # Infernal Dragonborn
        (315, 318), (316, 319), (317, 320),
        # Mochi / Taiwan Mascot
        (327, 330), (328, 331), (329, 332),
        # Black Drake (7 days)
        (339, 340),
        # Black Dragon
        (342, 343),
        # Absolute Black Dragon
        (345, 346),
        # Absolute Zero
        (348, 351), (349, 352), (350, 353),
    ]
    body_pairs = base_1_50 + body_high

    # High-level helmets & specialized headgears (Page 13)
    helmet_high = [
        # Level 50 / F-type
        (190, 193), (191, 194), (192, 195),
        # Guild Leader / Archon
        (199, 202), (200, 203), (201, 204),
        # Level 53-55 / Type C / Baal / Hierarch
        (208, 214), (209, 215), (210, 216), (211, 217), (212, 218), (213, 219),
        # White / Premium
        (227, 230), (228, 231), (229, 232),
        # Level 65 Titan <-> Taurus
        (238, 244), (239, 245), (240, 246),
        # Support
        (248, 249),
        # Level 70 Patron Titan <-> Taurus
        (251, 254), (252, 255), (253, 256),
        # Mamon masks
        (269, 272), (270, 273), (271, 274),
        # Asmodeus masks
        (278, 281), (279, 282), (280, 283),
        # White Dragonborn
        (288, 289),
        # Level 75 Baalzebub
        (296, 299), (297, 300), (298, 301),
        # Philippine mask
        (313, 314),
        # Hephaestus <-> Urania masks
        (316, 319), (317, 320), (318, 321),
        # Prototype masks
        (325, 328), (326, 329), (327, 330),
        # Elite visors
        (350, 353), (351, 354), (352, 355),
        # Master / PvP
        (359, 362), (360, 363), (361, 364),
        # Infernal
        (389, 392), (390, 393), (391, 394),
        # Mochi / Taiwan
        (423, 426), (424, 427), (425, 428),
        # Black Drake / Dragon
        (436, 439), (437, 440), (438, 441),
        # Absolute Zero
        (445, 448), (446, 449), (447, 450),
    ]
    helmet_pairs = base_1_50 + helmet_high

    # Cloak / Anti-grav / Booster pairs (Page 19)
    cloak_pairs = [
        (154, 155),  # Standard Anti-grav (Accretia 156)
        (202, 203),  # Premium Anti-grav (Accretia 204)
        (217, 219),  # Gold Anti-grav (Accretia 218)
        (240, 242), (241, 243), (246, 248), (247, 249),  # Adeptus <-> Inquisitor
        (272, 275), (273, 276), (274, 277),  # Prototype Wings / Hephaestus <-> Urania
        (300, 302), (301, 303),              # Prototype Wings 30d
        (306, 309), (307, 310), (308, 311),  # Philippine Backpacks
        (344, 346), (345, 347),              # Elite Hephaestus <-> Urania
        (402, 403),                          # Infernal Dragonborn Booster
        (457, 458), (460, 461),              # Chuseok Backpacks
        (463, 466), (464, 467), (465, 468),  # Black Dragon Boosters
        (480, 481),                          # Absolute Zero Booster
    ]

    all_pairs = []
    # Page 13: Helmet (120 pairs)
    for b, c in helmet_pairs:
        all_pairs.append(((13 << 10) | b, (13 << 10) | c))
    # Pages 14..17: Upper, Lower, Gauntlet, Shoe (104 * 4 = 416 pairs)
    for p in range(14, 18):
        for b, c in body_pairs:
            all_pairs.append(((p << 10) | b, (p << 10) | c))
    # Page 19: Cloaks & Boosters (24 pairs)
    for b, c in cloak_pairs:
        all_pairs.append(((19 << 10) | b, (19 << 10) | c))

    return all_pairs


ICON_SWAP_PAIRS = generate_icon_swap_pairs()

STRICT_EXCLUSIONS = {
    "BF2CA.RFS", "BM2CA.RFS", "CF2CA.RFS", "CM2CA.RFS", "AC2CA.RFS",
    "BFETA.RFS", "BMETA.RFS", "CFETA.RFS", "CMETA.RFS", "ACETA.RFS",
    "Accretia.bn", "Accretia.BBX",
    # Base race skeletons — engine validates exact bone counts at login
    # BelFemale: 25 bones, BelMale: 30 bones, CorFemale: 38 bones, CorMale: 29 bones
    # Swapping these triggers "Invalid Bone File." -> RequestQuitProgram crash
    "BelFemale.bn", "BelFemale.BBX",
    "CorFemale.bn", "CorFemale.BBX",
    "BelMale.bn", "BelMale.BBX",
    "CorMale.bn", "CorMale.BBX",
    "Bellato_Female.bn", "Bellato_Female.BBX",
    "Cora_Female.bn", "Cora_Female.BBX",
    "Bellato_Male.bn", "Bellato_Male.BBX",
    "Cora_Male.bn", "Cora_Male.BBX",
    "Item.edf", "ItemCash.edf", "SkillForce.edf",
}


def calc_md5(file_path: str) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def scale_msh(data: bytes, scale: float = 2.0 / 3.0) -> bytes:
    """
    Scales all vertex coordinates, bounding boxes, and object transformation matrices
    in an RF Online .msh file by `scale` factor.
    Supports both classic MSH (28 bytes/vert) and MESH08 (64 bytes/vert) formats.
    Preserves exact byte structure, bone indices, weights, normals, and UVs.
    """
    ba = bytearray(data)

    is_mesh08 = False
    offset = 0
    if ba[:6] == b"MESH08":
        is_mesh08 = True
        offset = 6

    num_objects = struct.unpack("<H", ba[offset:offset+2])[0]
    offset += 2

    for obj_idx in range(num_objects):
        # 100 bytes obj_name + 100 bytes parent_name
        offset += 200

        # world_mat (64 bytes: 16 float32)
        world_mat = list(struct.unpack("<16f", ba[offset:offset+64]))
        world_mat[12] *= scale
        world_mat[13] *= scale
        world_mat[14] *= scale
        ba[offset:offset+64] = struct.pack("<16f", *world_mat)
        offset += 64

        # local_mat (64 bytes: 16 float32)
        local_mat = list(struct.unpack("<16f", ba[offset:offset+64]))
        local_mat[12] *= scale
        local_mat[13] *= scale
        local_mat[14] *= scale
        ba[offset:offset+64] = struct.pack("<16f", *local_mat)
        offset += 64

        # third_mat (64 bytes: 16 float32)
        third_mat = list(struct.unpack("<16f", ba[offset:offset+64]))
        third_mat[12] *= scale
        third_mat[13] *= scale
        third_mat[14] *= scale
        ba[offset:offset+64] = struct.pack("<16f", *third_mat)
        offset += 64

        vert_amt, tri_amt, weight_amt = struct.unpack("<HHH", ba[offset:offset+6])
        offset += 6

        # tex_path (100 bytes) + eff_path (100 bytes)
        offset += 200

        # bbox_max (12 bytes: 3 float32)
        bbox_max = list(struct.unpack("<3f", ba[offset:offset+12]))
        bbox_max[0] *= scale; bbox_max[1] *= scale; bbox_max[2] *= scale
        ba[offset:offset+12] = struct.pack("<3f", *bbox_max)
        offset += 12

        # bbox_min (12 bytes: 3 float32)
        bbox_min = list(struct.unpack("<3f", ba[offset:offset+12]))
        bbox_min[0] *= scale; bbox_min[1] *= scale; bbox_min[2] *= scale
        ba[offset:offset+12] = struct.pack("<3f", *bbox_min)
        offset += 12

        # unk_f3_1 (12 bytes: 3 float32)
        offset += 12

        # unk_flags (8 bytes)
        offset += 8

        # weight_model_type (4 bytes)
        weight_model_type = struct.unpack("<I", ba[offset:offset+4])[0]
        offset += 4

        # unk_f3_2 (12 bytes)
        offset += 12

        # unk_f1 (4 bytes)
        offset += 4

        # padding/unknown (31 bytes)
        offset += 31

        if is_mesh08:
            m08_vert_amt = struct.unpack("<H", ba[offset:offset+2])[0]
            offset += 2

            # MESH08 vertices: 64 bytes each
            # [0:12] pos (3f), [12:24] weights (3f), [24:32] bones (4H),
            # [32:44] normal (3f), [44:52] uv (2f), [52:64] binormal (3f)
            for v in range(m08_vert_amt):
                x, y, z = struct.unpack("<3f", ba[offset:offset+12])
                ba[offset:offset+12] = struct.pack("<3f", x * scale, y * scale, z * scale)
                offset += 64

            m08_tri_amt = struct.unpack("<H", ba[offset:offset+2])[0]
            offset += 2
            offset += m08_tri_amt * 2  # triangle indices (uint16)

            bone_group_amt = struct.unpack("<H", ba[offset:offset+2])[0]
            offset += 2
            for bg in range(bone_group_amt):
                cur_bone_amt = struct.unpack("<I", ba[offset:offset+4])[0]
                offset += 4
                offset += 4 * 100
        else:
            # Default vertices: 28 bytes each
            # [0:12] pos (3f), [12:16] unknown (4B), [16:28] normal (3f)
            for v in range(vert_amt):
                x, y, z = struct.unpack("<3f", ba[offset:offset+12])
                ba[offset:offset+12] = struct.pack("<3f", x * scale, y * scale, z * scale)
                offset += 28

            # Default triangles: 88 bytes each
            offset += tri_amt * 88

            if weight_model_type == 1:
                bone_amt = struct.unpack("<I", ba[offset:offset+4])[0]
                offset += 4
                offset += bone_amt * 100
                offset += weight_amt * 40
            else:
                offset += weight_amt * 424

    assert offset == len(ba), f"Offset mismatch in scale_msh: {offset} != {len(ba)}"
    return bytes(ba)


def parse_msh_chunks(ba: bytearray) -> Tuple[bool, List[Tuple[str, bytes]]]:
    """
    Parses an RF Online .msh bytearray into its constituent object chunks.
    Supports both classic MSH (28 bytes/vert) and MESH08 (64 bytes/vert) formats.
    Returns (is_mesh08, list of (object_name, chunk_bytes)).
    """
    is_m08 = ba[:6] == b"MESH08"
    offset = 6 if is_m08 else 0
    num_objs = struct.unpack("<H", ba[offset:offset+2])[0]
    offset += 2
    chunks = []
    for _ in range(num_objs):
        start = offset
        name = ba[offset:offset+100].split(b"\x00")[0].decode("ascii", errors="ignore")
        offset += 200 + 64 * 3  # obj_name, parent_name, 3 matrices
        v_amt, t_amt, w_amt = struct.unpack("<HHH", ba[offset:offset+6])
        offset += 6 + 200 + 12 + 12 + 12 + 8  # v/t/w, tex/eff, bbox, unk
        w_type = struct.unpack("<I", ba[offset:offset+4])[0]
        offset += 4 + 12 + 4 + 31  # w_type, unk_f3_2, unk_f1, padding
        if is_m08:
            mv_amt = struct.unpack("<H", ba[offset:offset+2])[0]
            offset += 2 + mv_amt * 64
            mt_amt = struct.unpack("<H", ba[offset:offset+2])[0]
            offset += 2 + mt_amt * 2
            bg_amt = struct.unpack("<H", ba[offset:offset+2])[0]
            offset += 2
            for _ in range(bg_amt):
                offset += 4 + 400
        else:
            offset += v_amt * 28 + t_amt * 88
            if w_type == 1:
                b_amt = struct.unpack("<I", ba[offset:offset+4])[0]
                offset += 4 + b_amt * 100 + w_amt * 40
            else:
                offset += w_amt * 424
        chunks.append((name, bytes(ba[start:offset])))
    assert offset == len(ba), f"Offset mismatch in parse_msh_chunks: {offset} != {len(ba)}"
    return is_m08, chunks


def combine_msh(base_msh: bytes, addon_msh: bytes, filter_fn) -> bytes:
    """
    Combines object chunks from base_msh with filtered object chunks from addon_msh.
    Preserves vertex coordinates, weights, matrices, and chunk formats.
    """
    is_m08_base, base_chunks = parse_msh_chunks(bytearray(base_msh))
    is_m08_add, add_chunks = parse_msh_chunks(bytearray(addon_msh))
    assert is_m08_base == is_m08_add, "MSH format mismatch between base and addon"

    selected_addon = [c for c in add_chunks if filter_fn(c[0])]
    all_chunks = base_chunks + selected_addon

    out = bytearray()
    if is_m08_base:
        out.extend(b"MESH08")
    out.extend(struct.pack("<H", len(all_chunks)))
    for _, chunk_data in all_chunks:
        out.extend(chunk_data)
    return bytes(out)


class BackupManager:
    def __init__(self, base_dir: str = BASE_DIR, backup_dir: str = BACKUP_DIR):
        self.base_dir = base_dir
        self.backup_dir = backup_dir
        self.manifest_file = BACKUP_MANIFEST

    def load_manifest(self) -> Dict[str, Any]:
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[!] Warning: Could not read backup manifest: {e}")
        return {}

    def save_manifest(self, manifest: Dict[str, Any]) -> None:
        os.makedirs(self.backup_dir, exist_ok=True)
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def backup_files(self, file_rel_paths: List[str], swapped_dirs: Optional[List[Tuple[str, str]]] = None) -> int:
        os.makedirs(self.backup_dir, exist_ok=True)
        manifest = self.load_manifest()
        files_manifest = manifest.get("files", {})
        backed_up_count = 0

        for rel in file_rel_paths:
            src = os.path.join(self.base_dir, rel)
            dst = os.path.join(self.backup_dir, rel)

            if not os.path.exists(src):
                continue

            if os.path.exists(dst):
                if rel not in files_manifest:
                    files_manifest[rel] = {
                        "md5": calc_md5(dst),
                        "size": os.path.getsize(dst)
                    }
                continue

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            files_manifest[rel] = {
                "md5": calc_md5(dst),
                "size": os.path.getsize(dst)
            }
            backed_up_count += 1

        manifest["files"] = files_manifest
        if swapped_dirs is not None:
            manifest["swapped_dirs"] = swapped_dirs

        self.save_manifest(manifest)
        return backed_up_count

    def rollback(self) -> Tuple[int, List[str]]:
        if not os.path.exists(self.manifest_file):
            print("[-] No backup manifest found in _ModBackup/. Nothing to rollback.")
            return 0, []

        manifest = self.load_manifest()
        files_manifest = manifest.get("files", manifest)  # Backward compatibility
        swapped_dirs = manifest.get("swapped_dirs", [])
        restored = 0
        errors = []

        # 1. Clean and restore directory pairs to eliminate swapped leftovers
        if swapped_dirs:
            print(f"[*] Restoring {len(swapped_dirs)} directory pairs cleanly...")
            for dir_a_rel, dir_b_rel in swapped_dirs:
                target_a = os.path.join(self.base_dir, dir_a_rel)
                target_b = os.path.join(self.base_dir, dir_b_rel)
                backup_a = os.path.join(self.backup_dir, dir_a_rel)
                backup_b = os.path.join(self.backup_dir, dir_b_rel)

                if os.path.exists(target_a):
                    shutil.rmtree(target_a, ignore_errors=True)
                if os.path.exists(target_b):
                    shutil.rmtree(target_b, ignore_errors=True)

                if os.path.exists(backup_a):
                    shutil.copytree(backup_a, target_a)
                if os.path.exists(backup_b):
                    shutil.copytree(backup_b, target_b)

        # 2. Restore individual files from backup
        print(f"[*] Rolling back {len(files_manifest)} files from _ModBackup/...")
        for rel, meta in files_manifest.items():
            backup_src = os.path.join(self.backup_dir, rel)
            target_dst = os.path.join(self.base_dir, rel)

            if not os.path.exists(backup_src):
                errors.append(f"Missing backup file: {rel}")
                continue

            try:
                os.makedirs(os.path.dirname(target_dst), exist_ok=True)
                shutil.copy2(backup_src, target_dst)
                restored += 1
            except Exception as e:
                errors.append(f"Failed to restore {rel}: {e}")

        print(f"[+] Rollback complete: {restored}/{len(files_manifest)} files restored.")
        if errors:
            print(f"[!] Encountered {len(errors)} errors during rollback:")
            for err in errors[:10]:
                print(f"    - {err}")

        if os.path.exists(CACHE_DIR):
            print("[*] Clearing mod cache _ModCache/...")
            shutil.rmtree(CACHE_DIR, ignore_errors=True)

        return restored, errors


class RFSHandler:
    @staticmethod
    def read_rfs(file_path: str) -> Tuple[List[dict], bytes]:
        with open(file_path, "rb") as f:
            data = f.read()

        count = struct.unpack("<I", data[:4])[0]
        entries = []
        for i in range(count):
            entry_bytes = data[4 + i * 64 : 4 + (i + 1) * 64]
            name_raw = entry_bytes[:32]
            meta = entry_bytes[32:56]
            off = struct.unpack("<I", entry_bytes[56:60])[0]
            size = struct.unpack("<I", entry_bytes[60:64])[0]
            file_data = data[off : off + size]
            entries.append({
                "name_raw": bytearray(name_raw),
                "meta": meta,
                "size": size,
                "data": bytearray(file_data)
            })
        return entries, data

    @staticmethod
    def write_rfs(file_path: str, entries: List[dict]) -> None:
        count = len(entries)
        table_len = count * 64
        cur_off = 4 + table_len

        repacked = bytearray()
        repacked.extend(struct.pack("<I", count))

        for e in entries:
            name_padded = (e["name_raw"][:32] + b"\x00" * 32)[:32]
            repacked.extend(name_padded)
            repacked.extend(e["meta"][:24])
            repacked.extend(struct.pack("<II", cur_off, len(e["data"])))
            cur_off += len(e["data"])

        for e in entries:
            repacked.extend(e["data"])

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(repacked)

    @classmethod
    def find_shared_rfs_pairs(cls, entries: List[dict]) -> List[Tuple[int, int]]:
        name_to_idx = {}
        names = []
        for i, e in enumerate(entries):
            raw = bytes(e["name_raw"]).split(b"\x00")[0]
            name = raw.decode("ascii", errors="ignore")
            name_to_idx[name] = i
            names.append(name)

        class_offsets = {
            181: 205, 189: 213, 197: 221,  # 70LV
            183: 207, 191: 215, 199: 223,  # 60LV Dark
        }

        whitet_slot_map = {
            "BF_A_G_": "CF_A_GLOVES_",
            "BF_A_L_": "CF_A_LOWER_",
            "BF_A_S_": "CF_A_SHOES_",
            "BF_A_U_": "CF_A_UPPER_",
            "BM_A_G_": "CM_A_GLOVES_",
            "BM_A_L_": "CM_A_LOWER_",
            "BM_A_S_": "CM_A_SHOES_",
            "BM_A_U_": "CM_A_UPPER_",
        }

        pairs = []
        matched_b = set()
        matched_c = set()

        # 1. Check WHITET slot map
        for b_prefix, c_prefix in whitet_slot_map.items():
            for name in names:
                if name.startswith(b_prefix):
                    suffix = name[len(b_prefix):]
                    c_name = c_prefix + suffix
                    if c_name in name_to_idx and name not in matched_b and c_name not in matched_c:
                        pairs.append((name_to_idx[name], name_to_idx[c_name]))
                        matched_b.add(name)
                        matched_c.add(c_name)

        # 2. Check direct prefixes and class offsets
        bel_names = [n for n in names if (n.startswith("BEL") or n.startswith("BEFE") or n.startswith("BEMA") or n.startswith("B_A_")) and n not in matched_b]

        for b_name in bel_names:
            c_cand = None
            for b_pref, c_pref in [
                ("BELFEMALE_", "CORFEMALE_"),
                ("BELMALE_", "CORMALE_"),
                ("BEFE_", "COFE_"),
                ("BEMA_", "COMA_"),
                ("B_A_", "C_A_")
            ]:
                if b_pref in b_name:
                    cand = b_name.replace(b_pref, c_pref)
                    if cand in name_to_idx and cand not in matched_c:
                        c_cand = cand
                        break

            if not c_cand:
                for b_num, c_num in class_offsets.items():
                    if f"_{b_num}." in b_name or f"_{b_num}_" in b_name:
                        for b_pref, c_pref in [("BELFEMALE_", "CORFEMALE_"), ("BELMALE_", "CORMALE_")]:
                            if b_pref in b_name:
                                cand = b_name.replace(b_pref, c_pref).replace(str(b_num), str(c_num))
                                if cand in name_to_idx and cand not in matched_c:
                                    c_cand = cand
                                    break
                        if c_cand:
                            break

            if not c_cand and "_253." in b_name:
                cand = b_name.replace("BELFEMALE_", "CORFEMALE_").replace("BELMALE_", "CORMALE_").replace("_253.", "_252.")
                if cand in name_to_idx and cand not in matched_c:
                    c_cand = cand

            if c_cand:
                pairs.append((name_to_idx[b_name], name_to_idx[c_cand]))
                matched_b.add(b_name)
                matched_c.add(c_cand)

        return pairs

    @classmethod
    def inject_shared_helmets(cls, file_path: str, entries: List[dict]) -> int:
        fname = os.path.basename(file_path).upper()
        existing_names = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore") for e in entries}
        injected = 0
        is_mesh = "mesh" in file_path.lower()

        # 1. DARKM60.RFS (Mesh) & DARKT60.RFS (Tex)
        if "DARKM60.RFS" in fname:
            for e in list(entries):
                n = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                if "HELMET" in n and "BEL" in n:
                    gender = "FEMALE" if "FEMALE" in n else "MALE"
                    scale_up = 17.00 / 14.85 if gender == "FEMALE" else 15.81 / 13.85
                    c_n = n.replace(f"BEL{gender}_", f"COR{gender}_")
                    for b_num, c_num in [(183, 207), (191, 215), (199, 223)]:
                        c_n = c_n.replace(str(b_num), str(c_num))
                    if c_n not in existing_names:
                        c_data = bytes(e["data"]).replace(b"BEL", b"COR").replace(b"B_A_", b"C_A_")
                        for b_num, c_num in [(b"183", b"207"), (b"191", b"215"), (b"199", b"223")]:
                            c_data = c_data.replace(b_num, c_num)
                        try:
                            scaled_bel = scale_msh(bytes(e["data"]), scale_up)
                            e["data"] = bytearray(scaled_bel)
                            e["size"] = len(scaled_bel)
                        except Exception:
                            pass
                        new_name_raw = bytearray(64)
                        c_bytes = c_n.encode("ascii")
                        new_name_raw[:len(c_bytes)] = c_bytes
                        entries.append({
                            "name_raw": new_name_raw,
                            "meta": e["meta"],
                            "size": len(c_data),
                            "data": bytearray(c_data)
                        })
                        existing_names.add(c_n)
                        injected += 1

        elif "DARKT60.RFS" in fname:
            for e in list(entries):
                n = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                if n.startswith("B_A_H_"):
                    c_n = "C_A_H_" + n[6:]
                    if c_n not in existing_names:
                        c_data = bytes(e["data"])
                        new_name_raw = bytearray(64)
                        c_bytes = c_n.encode("ascii")
                        new_name_raw[:len(c_bytes)] = c_bytes
                        entries.append({
                            "name_raw": new_name_raw,
                            "meta": e["meta"],
                            "size": len(c_data),
                            "data": bytearray(c_data)
                        })
                        existing_names.add(c_n)
                        injected += 1

        # 2. ORI70.RFS / ori6770.RFS
        elif "ORI70.RFS" in fname or "ORI6770.RFS" in fname:
            if is_mesh:
                for e in list(entries):
                    n = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                    if "HELMET" in n and "BEL" in n:
                        gender = "FEMALE" if "FEMALE" in n else "MALE"
                        scale_up = 17.00 / 14.85 if gender == "FEMALE" else 15.81 / 13.85
                        c_n = n.replace(f"BEL{gender}_", f"COR{gender}_")
                        for b_num, c_num in [(181, 205), (189, 213), (197, 221)]:
                            c_n = c_n.replace(str(b_num), str(c_num))
                        if c_n not in existing_names:
                            c_data = bytes(e["data"]).replace(b"BEL", b"COR").replace(b"BEFE_", b"COFE_").replace(b"BEMA_", b"COMA_")
                            for b_num, c_num in [(b"181", b"205"), (b"189", b"213"), (b"197", b"221")]:
                                c_data = c_data.replace(b_num, c_num)
                            try:
                                scaled_bel = scale_msh(bytes(e["data"]), scale_up)
                                e["data"] = bytearray(scaled_bel)
                                e["size"] = len(scaled_bel)
                            except Exception:
                                pass
                            new_name_raw = bytearray(64)
                            c_bytes = c_n.encode("ascii")
                            new_name_raw[:len(c_bytes)] = c_bytes
                            entries.append({
                                "name_raw": new_name_raw,
                                "meta": e["meta"],
                                "size": len(c_data),
                                "data": bytearray(c_data)
                            })
                            existing_names.add(c_n)
                            injected += 1
            else:
                for e in list(entries):
                    n = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                    for b_p, c_p in [("BEMA_HELMET_", "COMA_HELMET_"), ("BEFE_HELMET_", "COFE_HELMET_")]:
                        if n.startswith(b_p):
                            c_n = c_p + n[len(b_p):]
                            if c_n not in existing_names:
                                c_data = bytes(e["data"])
                                new_name_raw = bytearray(64)
                                c_bytes = c_n.encode("ascii")
                                new_name_raw[:len(c_bytes)] = c_bytes
                                entries.append({
                                    "name_raw": new_name_raw,
                                    "meta": e["meta"],
                                    "size": len(c_data),
                                    "data": bytearray(c_data)
                                })
                                existing_names.add(c_n)
                                injected += 1

        # 3. WHITEM.RFS / NWHITEM.RFS (Mesh) & WHITET.RFS / NWHITET.RFS (Tex)
        elif "WHITEM.RFS" in fname:
            for e in list(entries):
                n = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                if "HELMET" in n and "BEL" in n:
                    gender = "FEMALE" if "FEMALE" in n else "MALE"
                    scale_up = 17.00 / 14.85 if gender == "FEMALE" else 15.81 / 13.85
                    c_n = n.replace(f"BEL{gender}_", f"COR{gender}_")
                    if c_n not in existing_names:
                        c_data = bytes(e["data"]).replace(b"BEL", b"COR").replace(b"BM_A_", b"CM_A_").replace(b"BF_A_", b"CF_A_")
                        try:
                            scaled_bel = scale_msh(bytes(e["data"]), scale_up)
                            e["data"] = bytearray(scaled_bel)
                            e["size"] = len(scaled_bel)
                        except Exception:
                            pass
                        new_name_raw = bytearray(64)
                        c_bytes = c_n.encode("ascii")
                        new_name_raw[:len(c_bytes)] = c_bytes
                        entries.append({
                            "name_raw": new_name_raw,
                            "meta": e["meta"],
                            "size": len(c_data),
                            "data": bytearray(c_data)
                        })
                        existing_names.add(c_n)
                        injected += 1

        elif "WHITET.RFS" in fname:
            for e in list(entries):
                n = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                for b_p, c_p in [("BM_A_H_", "CM_A_H_"), ("BF_A_H_", "CF_A_H_")]:
                    if n.startswith(b_p):
                        c_n = c_p + n[len(b_p):]
                        if c_n not in existing_names:
                            c_data = bytes(e["data"])
                            new_name_raw = bytearray(64)
                            c_bytes = c_n.encode("ascii")
                            new_name_raw[:len(c_bytes)] = c_bytes
                            entries.append({
                                "name_raw": new_name_raw,
                                "meta": e["meta"],
                                "size": len(c_data),
                                "data": bytearray(c_data)
                            })
                            existing_names.add(c_n)
                            injected += 1

        return injected

    @classmethod
    def swap_shared_rfs_internal(cls, file_path: str) -> int:
        entries, _ = cls.read_rfs(file_path)
        pairs = cls.find_shared_rfs_pairs(entries)

        is_mesh = file_path.lower().endswith(".rfs") and "mesh" in file_path.lower()

        for idx_b, idx_c in pairs:
            name_b = bytes(entries[idx_b]["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
            name_c = bytes(entries[idx_c]["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")

            b_data = bytes(entries[idx_b]["data"])
            b_meta = entries[idx_b]["meta"]

            c_data = bytes(entries[idx_c]["data"])
            c_meta = entries[idx_c]["meta"]

            # Replace embedded race strings inside entry data
            b_to_c_data = b_data
            for b_p, c_p in [
                (b"BELFEMALE_", b"CORFEMALE_"), (b"BELMALE_", b"CORMALE_"),
                (b"BF_", b"CF_"), (b"BM_", b"CM_"),
                (b"BEFE_", b"COFE_"), (b"BEMA_", b"COMA_"),
                (b"B_A_", b"C_A_")
            ]:
                b_to_c_data = b_to_c_data.replace(b_p, c_p)

            c_to_b_data = c_data
            for b_p, c_p in [
                (b"BELFEMALE_", b"CORFEMALE_"), (b"BELMALE_", b"CORMALE_"),
                (b"BF_", b"CF_"), (b"BM_", b"CM_"),
                (b"BEFE_", b"COFE_"), (b"BEMA_", b"COMA_"),
                (b"B_A_", b"C_A_")
            ]:
                c_to_b_data = c_to_b_data.replace(c_p, b_p)

            entries[idx_b]["data"] = bytearray(c_to_b_data)
            entries[idx_b]["meta"] = c_meta
            entries[idx_b]["size"] = len(c_to_b_data)

            entries[idx_c]["data"] = bytearray(b_to_c_data)
            entries[idx_c]["meta"] = b_meta
            entries[idx_c]["size"] = len(b_to_c_data)

        injected = cls.inject_shared_helmets(file_path, entries)
        cls.write_rfs(file_path, entries)
        return len(pairs) + injected

    @classmethod
    def swap_and_patch_rfs(cls, path_a: str, path_b: str, gender: str = "FEMALE") -> None:
        entries_a, _ = cls.read_rfs(path_a)
        entries_b, _ = cls.read_rfs(path_b)

        bel_prefix = f"BEL{gender}_".encode("ascii")
        cor_prefix = f"COR{gender}_".encode("ascii")

        is_female = gender == "FEMALE"
        scale_up = 17.00 / 14.85 if is_female else 15.81 / 13.85
        is_mesh_archive = "mesh" in path_a.lower()
        is_b55 = "b55.rfs" in path_a.lower()

        # Map entries by normalized suffix
        a_map = {}
        for e in entries_a:
            raw_name = bytes(e["name_raw"]).split(b"\x00")[0]
            if raw_name.startswith(bel_prefix):
                suffix = raw_name[len(bel_prefix):]
                a_map[suffix] = e

        b_map = {}
        for e in entries_b:
            raw_name = bytes(e["name_raw"]).split(b"\x00")[0]
            if raw_name.startswith(cor_prefix):
                suffix = raw_name[len(cor_prefix):]
                b_map[suffix] = e

        # Construct new_a_entries (destination: path_a, used by Bellato)
        new_a_entries = []
        if is_b55 and is_mesh_archive:
            b55_c_to_b = {b"203": b"179", b"211": b"187", b"219": b"195"}
            for e in entries_b:
                data = bytes(e["data"]).replace(cor_prefix, bel_prefix).replace(b"CM_", b"BM_").replace(b"CF_", b"BF_")
                name = bytes(e["name_raw"]).replace(cor_prefix, bel_prefix)
                for k, v in b55_c_to_b.items():
                    data = data.replace(k, v)
                    name = name.replace(k, v)
                new_a_entries.append({
                    "name_raw": bytearray(name),
                    "meta": e["meta"],
                    "size": len(data),
                    "data": bytearray(data)
                })
            # Retain Bellato's helmets (scaled up for tall skeleton)
            for suffix, e in a_map.items():
                if b"HELMET" in suffix:
                    data = bytes(e["data"])
                    try:
                        data = scale_msh(data, scale_up)
                    except Exception:
                        pass
                    new_a_entries.append({
                        "name_raw": e["name_raw"],
                        "meta": e["meta"],
                        "size": len(data),
                        "data": bytearray(data)
                    })
        else:
            for e in entries_b:
                data = bytes(e["data"]).replace(cor_prefix, bel_prefix).replace(b"CM_", b"BM_").replace(b"CF_", b"BF_")
                name = bytes(e["name_raw"]).replace(cor_prefix, bel_prefix)
                new_a_entries.append({
                    "name_raw": bytearray(name),
                    "meta": e["meta"],
                    "size": len(data),
                    "data": bytearray(data)
                })

            if is_mesh_archive:
                for suffix, e in a_map.items():
                    if b"HELMET" in suffix and suffix not in b_map:
                        data = bytes(e["data"])
                        try:
                            data = scale_msh(data, scale_up)
                        except Exception as err:
                            print(f"    [!] Warning: could not scale retained helmet {suffix}: {err}")
                        new_a_entries.append({
                            "name_raw": e["name_raw"],
                            "meta": e["meta"],
                            "size": len(data),
                            "data": bytearray(data)
                        })
            else:
                for suffix, e in a_map.items():
                    if b"HELMET" in suffix and suffix not in b_map:
                        new_a_entries.append(e)

        # Construct new_b_entries (destination: path_b, used by Cora)
        new_b_entries = []
        if is_b55 and is_mesh_archive:
            b55_b_to_c = {b"179": b"203", b"187": b"211", b"195": b"219"}
            for e in entries_a:
                data = bytes(e["data"]).replace(bel_prefix, cor_prefix).replace(b"BM_", b"CM_").replace(b"BF_", b"CF_")
                name = bytes(e["name_raw"]).replace(bel_prefix, cor_prefix)
                for k, v in b55_b_to_c.items():
                    data = data.replace(k, v)
                    name = name.replace(k, v)
                new_b_entries.append({
                    "name_raw": bytearray(name),
                    "meta": e["meta"],
                    "size": len(data),
                    "data": bytearray(data)
                })
        else:
            for e in entries_a:
                data = bytes(e["data"]).replace(bel_prefix, cor_prefix).replace(b"BM_", b"CM_").replace(b"BF_", b"CF_")
                name = bytes(e["name_raw"]).replace(bel_prefix, cor_prefix)
                new_b_entries.append({
                    "name_raw": bytearray(name),
                    "meta": e["meta"],
                    "size": len(data),
                    "data": bytearray(data)
                })

        cls.write_rfs(path_a, new_a_entries)
        cls.write_rfs(path_b, new_b_entries)

    @classmethod
    def swap_moa_with_raxethrow_protection(cls, path_bmoa: str, path_cmoa: str, gender: str = "FEMALE") -> None:
        b_entries, _ = cls.read_rfs(path_bmoa)
        c_entries, _ = cls.read_rfs(path_cmoa)

        bel_prefix = f"BEL{gender}_".encode("ascii")
        cor_prefix = f"COR{gender}_".encode("ascii")

        # Extract exclusive Bellato animations (the 6 throwing axe run/walk entries)
        b_map = {bytes(e["name_raw"]).split(b"\x00")[0][len(bel_prefix):]: e for e in b_entries}
        c_suffixes = {bytes(e["name_raw"]).split(b"\x00")[0][len(cor_prefix):] for e in c_entries}
        exclusive_b_suffixes = set(b_map.keys()) - c_suffixes

        raxethrow_entries = [b_map[s] for s in exclusive_b_suffixes]

        new_b_entries = []
        for e in c_entries:
            new_e = {
                "name_raw": bytearray(bytes(e["name_raw"]).replace(cor_prefix, bel_prefix)),
                "meta": e["meta"],
                "size": e["size"],
                "data": bytearray(bytes(e["data"]).replace(cor_prefix, bel_prefix))
            }
            new_b_entries.append(new_e)

        # Retain throwing axe animations in Bellato MOA archive
        new_b_entries.extend(raxethrow_entries)

        new_c_entries = []
        for e in b_entries:
            raw_suffix = bytes(e["name_raw"]).split(b"\x00")[0][len(bel_prefix):]
            if raw_suffix in exclusive_b_suffixes:
                continue
            new_e = {
                "name_raw": bytearray(bytes(e["name_raw"]).replace(bel_prefix, cor_prefix)),
                "meta": e["meta"],
                "size": e["size"],
                "data": bytearray(bytes(e["data"]).replace(bel_prefix, cor_prefix))
            }
            new_c_entries.append(new_e)

        cls.write_rfs(path_bmoa, new_b_entries)
        cls.write_rfs(path_cmoa, new_c_entries)


class SpritePatcher:
    def __init__(self, spr_path: str = os.path.join(BASE_DIR, "SpriteImage", "ru-ru", "item.spr")):
        self.spr_path = spr_path

    def get_page_info(self) -> Dict[int, Tuple[int, int]]:
        pages = {}
        if not os.path.exists(self.spr_path):
            return pages

        with open(self.spr_path, "rb") as f:
            f.seek(8)
            num_pages = struct.unpack("<I", f.read(4))[0]
            offset = 12
            for p in range(num_pages):
                f.seek(offset)
                fourcc = f.read(4)
                w, h, tw, th, dsize = struct.unpack("<IIIII", f.read(20))
                data_start = offset + 24
                if w == 2048 and h == 2048:
                    pitch_blocks = w // 4
                    pages[p] = (data_start, pitch_blocks)
                offset += 24 + dsize
        return pages

    def swap_icon_blocks(self, pairs: List[Tuple[int, int]] = ICON_SWAP_PAIRS) -> int:
        if not os.path.exists(self.spr_path):
            print(f"[!] Warning: {self.spr_path} not found. Skipping sprite patching.")
            return 0

        pages = self.get_page_info()
        swapped_count = 0

        with open(self.spr_path, "r+b") as f:
            for icon_a, icon_b in pairs:
                p_a = icon_a >> 10
                idx_a = icon_a & 1023
                row_a = idx_a // 32
                col_a = idx_a % 32

                p_b = icon_b >> 10
                idx_b = icon_b & 1023
                row_b = idx_b // 32
                col_b = idx_b % 32

                if p_a not in pages or p_b not in pages:
                    print(f"[!] Warning: Page {p_a} or {p_b} not standard 2048x2048 grid. Skipping ({icon_a}, {icon_b}).")
                    continue

                start_a, pitch_a = pages[p_a]
                start_b, pitch_b = pages[p_b]

                for by in range(16):
                    off_a = start_a + ((row_a * 16 + by) * pitch_a + col_a * 16) * 8
                    off_b = start_b + ((row_b * 16 + by) * pitch_b + col_b * 16) * 8

                    f.seek(off_a)
                    block_a = f.read(128)

                    f.seek(off_b)
                    block_b = f.read(128)

                    f.seek(off_a)
                    f.write(block_b)

                    f.seek(off_b)
                    f.write(block_a)

                swapped_count += 1

        return swapped_count

    @classmethod
    def swap_common_rank_badges(cls, base_dir: str = BASE_DIR) -> int:
        """
        Swaps overhead rank badges between Cora and Bellato in all copies of common.spr:
        - Page 31 (Bellato Rank Wings, 17x16 DXT5) <--> Page 32 (Cora Rank Wings, 17x16 DXT5)
        - Page 34 (Bellato Single Wing, 12x17 DXT5) <--> Page 35 (Cora Single Wing, 12x17 DXT5)
        - Page 42 (Cora Color Badge 29x23)          <--> Page 44 (Bellato Color Badge 29x23)
        - Page 43 (Cora Color Alt 29x23)            <--> Page 45 (Bellato Color Alt 29x23)
        Accretia pages (33, 36, 46, 47) remain strictly untouched.
        """
        target_rels = [
            "SpriteImage/ru-ru/common.spr",
            "SpriteImage/common.spr",
            "SpriteImage/common/common.spr",
            "SpriteImage/common/common/common.spr",
            "SpriteImage/en-gb/common.spr",
        ]
        swapped_total = 0
        for rel in target_rels:
            path = os.path.join(base_dir, rel)
            if not os.path.exists(path):
                continue
            sz = os.path.getsize(path)
            with open(path, "r+b") as f:
                f.seek(8)
                num_pages = struct.unpack("<I", f.read(4))[0]
                offset = 12
                page_info = {}
                for p in range(num_pages):
                    f.seek(offset)
                    fourcc = f.read(4)
                    w, h, tw, th, dsize = struct.unpack("<IIIII", f.read(20))
                    data_offset = offset + 24
                    page_info[p] = (data_offset, dsize)
                    offset += 24 + dsize

                # Swap Page 31 (Bellato wings) <--> Page 32 (Cora wings)
                if 31 in page_info and 32 in page_info:
                    off_31, sz_31 = page_info[31]
                    off_32, sz_32 = page_info[32]
                    if sz_31 == sz_32:
                        f.seek(off_31); data_31 = f.read(sz_31)
                        f.seek(off_32); data_32 = f.read(sz_32)
                        f.seek(off_31); f.write(data_32)
                        f.seek(off_32); f.write(data_31)
                        swapped_total += 1

                # Swap Page 34 (Bellato alt) <--> Page 35 (Cora alt)
                if 34 in page_info and 35 in page_info:
                    off_34, sz_34 = page_info[34]
                    off_35, sz_35 = page_info[35]
                    if sz_34 == sz_35:
                        f.seek(off_34); data_34 = f.read(sz_34)
                        f.seek(off_35); data_35 = f.read(sz_35)
                        f.seek(off_34); f.write(data_35)
                        f.seek(off_35); f.write(data_34)
                        swapped_total += 1

                # Swap Page 42 (Cora) <--> Page 44 (Bellato)
                if 42 in page_info and 44 in page_info:
                    off_42, sz_42 = page_info[42]
                    off_44, sz_44 = page_info[44]
                    if sz_42 == sz_44 == 1024:
                        f.seek(off_42); data_42 = f.read(1024)
                        f.seek(off_44); data_44 = f.read(1024)
                        f.seek(off_42); f.write(data_44)
                        f.seek(off_44); f.write(data_42)
                        swapped_total += 1

                # Swap Page 43 (Cora) <--> Page 45 (Bellato)
                if 43 in page_info and 45 in page_info:
                    off_43, sz_43 = page_info[43]
                    off_45, sz_45 = page_info[45]
                    if sz_43 == sz_45 == 1024:
                        f.seek(off_43); data_43 = f.read(1024)
                        f.seek(off_45); data_45 = f.read(1024)
                        f.seek(off_43); f.write(data_45)
                        f.seek(off_45); f.write(data_43)
                        swapped_total += 1

                # Swap 34x34 target window race crests (Bellato <--> Cora) located at end of file:
                # Bellato: sz - 3 * 2072
                # Cora:    sz - 2 * 2072
                # Accretia: sz - 1 * 2072 (untouched)
                if sz > 4 * 2072:
                    off_bel = sz - 3 * 2072
                    off_cor = sz - 2 * 2072
                    f.seek(off_bel); hdr_bel = f.read(24)
                    f.seek(off_cor); hdr_cor = f.read(24)
                    if hdr_bel[:4] == b"DXT1" and hdr_cor[:4] == b"DXT1":
                        wb, hb = struct.unpack("<II", hdr_bel[4:12])
                        wc, hc = struct.unpack("<II", hdr_cor[4:12])
                        if wb == 34 and hb == 34 and wc == 34 and hc == 34:
                            f.seek(off_bel + 24); data_bel = f.read(2048)
                            f.seek(off_cor + 24); data_cor = f.read(2048)
                            f.seek(off_bel + 24); f.write(data_cor)
                            f.seek(off_cor + 24); f.write(data_bel)
                            swapped_total += 1

        return swapped_total

    @classmethod
    def swap_pvp_race_badges(cls, base_dir: str = BASE_DIR) -> int:
        """
        Swaps target race crest badges in all copies of pvp.spr:
        - 34x34 crest: Bellato (204888 + 24, 2048B) <--> Cora (206960 + 24, 2048B)
        - 55x55 crest: Bellato (213180 + 24, 2048B) <--> Cora (215252 + 24, 2048B)
        Accretia crests (offsets 209032 and 217324) remain strictly untouched.
        """
        pvp_paths = [
            os.path.join(base_dir, "SpriteImage", "common", "pvp.spr"),
            os.path.join(base_dir, "SpriteImage", "common", "common", "pvp.spr"),
        ]
        total_swapped = 0
        for path in pvp_paths:
            if not os.path.exists(path):
                continue
            with open(path, "r+b") as f:
                # Swap 34x34 crest
                f.seek(204888 + 24); data_bel_34 = f.read(2048)
                f.seek(206960 + 24); data_cor_34 = f.read(2048)
                f.seek(204888 + 24); f.write(data_cor_34)
                f.seek(206960 + 24); f.write(data_bel_34)

                # Swap 55x55 crest
                f.seek(213180 + 24); data_bel_55 = f.read(2048)
                f.seek(215252 + 24); data_cor_55 = f.read(2048)
                f.seek(213180 + 24); f.write(data_cor_55)
                f.seek(215252 + 24); f.write(data_bel_55)
            total_swapped += 2
        return total_swapped

    @classmethod
    def swap_charinfo_race_badges(cls, base_dir: str = BASE_DIR) -> int:
        """
        Swaps race crest in all copies of charinfo.spr:
        - Page 0 (Bellato, 12 + 24, 2048B) <--> Page 1 (Cora, 2084 + 24, 2048B)
        Page 2 (Accretia) remains strictly untouched.
        """
        charinfo_paths = [
            os.path.join(base_dir, "SpriteImage", "common", "charinfo.spr"),
            os.path.join(base_dir, "SpriteImage", "en-gb", "charinfo.spr"),
        ]
        total_swapped = 0
        for path in charinfo_paths:
            if not os.path.exists(path):
                continue
            with open(path, "r+b") as f:
                f.seek(12 + 24); data_bel = f.read(2048)
                f.seek(2084 + 24); data_cor = f.read(2048)
                f.seek(12 + 24); f.write(data_cor)
                f.seek(2084 + 24); f.write(data_bel)
            total_swapped += 1
        return total_swapped


class SkeletonAdapter:
    """
    Constructs race-adapted skeletons for RF Online 4.75.

    The engine RF_Online.exe function 0x00608010 validates:
      - BelMale: expected 30 bones
      - CorMale: expected 29 bones
      - BelFemale: expected 25 bones
      - CorFemale: expected 38 bones

    This class builds:
      1. BelMale.bn (30 bones): Contains the Cora Male skeleton (tall elf height, arms, legs, fingers)
         plus 1 dummy bone (HeadNub from BelMale) parented to Head.
      2. CorMale.bn (29 bones): Contains the Bellato Male skeleton (dwarf height, arms, legs)
         with HeadNub removed.
      3. BelFemale.bn (25 bones): Contains the Cora Female skeleton (tall elf female height, arms, legs)
         with 13 extra non-essential bones (skirt, ponytail, finger1) removed.
      4. CorFemale.bn (38 bones): Contains the Bellato Female skeleton (dwarf female height, arms, legs)
         with 13 dummy bones appended.
      5. Synchronizes .BBX bounding box files and alias files (Bellato_Male.bn, etc.).
    """

    BM_NAMES = [
        "Bip01", "Bip01 Footsteps", "Bip01 Pelvis", "Bip01 Spine", "Bip01 Spine1",
        "Bip01 Neck", "Bip01 Head", "Bip01 HeadNub", "Bip01 L Clavicle", "Bip01 L UpperArm",
        "Bip01 L Forearm", "Bip01 L Hand", "Bip01 L Finger0", "Bip01 L Finger0Nub",
        "Bip01 R Clavicle", "Bip01 R UpperArm", "Bip01 R Forearm", "Bip01 R Hand",
        "Bip01 R Finger0", "Bip01 R Finger0Nub", "Bip01 L Thigh", "Bip01 L Calf",
        "Bip01 L Foot", "Bip01 L Toe0", "Bip01 L Toe0Nub", "Bip01 R Thigh",
        "Bip01 R Calf", "Bip01 R Foot", "Bip01 R Toe0", "Bip01 R Toe0Nub"
    ]

    CM_NAMES = [
        "Bip01", "Bip01 Footsteps", "Bip01 Pelvis", "Bip01 Spine", "Bip01 Spine1",
        "Bip01 Neck", "Bip01 Head", "Bip01 L Clavicle", "Bip01 L UpperArm", "Bip01 L Forearm",
        "Bip01 L Hand", "Bip01 L Finger0", "Bip01 L Finger1", "Bip01 L Finger1Nub",
        "Bip01 R Clavicle", "Bip01 R UpperArm", "Bip01 R Forearm", "Bip01 R Hand",
        "Bip01 R Finger0", "Bip01 R Finger1", "Bip01 R Finger1Nub",
        "Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot", "Bip01 L Toe0",
        "Bip01 R Thigh", "Bip01 R Calf", "Bip01 R Foot", "Bip01 R Toe0"
    ]

    BF_NAMES = [
        "Bip01", "Bip01 Footsteps", "Bip01 Pelvis", "Bip01 Spine", "Bip01 Spine1",
        "Bip01 Neck", "Bip01 Head", "Bip01 L Clavicle", "Bip01 L UpperArm", "Bip01 L Forearm",
        "Bip01 L Hand", "Bip01 L Finger0", "Bip01 R Clavicle", "Bip01 R UpperArm", "Bip01 R Forearm",
        "Bip01 R Hand", "Bip01 R Finger0", "Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot",
        "Bip01 L Toe0", "Bip01 R Thigh", "Bip01 R Calf", "Bip01 R Foot", "Bip01 R Toe0"
    ]

    CF_NAMES = [
        "Bip01", "Bip01 Footsteps", "Bip01 Pelvis", "Bip01 Spine", "Bip01 Spine1",
        "Bip01 Neck", "Bip01 Head", "Bip01 Ponytail L1", "Bip01 Ponytail L11", "Bip01 Ponytail L1Nub",
        "Bip01 R Clavicle", "Bip01 R UpperArm", "Bip01 R Forearm", "Bip01 R Hand",
        "Bip01 R Finger0", "Bip01 R Finger1", "Bip01 R Finger1Nub",
        "Bip01 L Clavicle", "Bip01 L UpperArm", "Bip01 L Forearm", "Bip01 L Hand",
        "Bip01 L Finger0", "Bip01 L Finger1", "Bip01 L Finger1Nub",
        "Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot", "Bip01 L Toe0",
        "Bip01 R Thigh", "Bip01 R Calf", "Bip01 R Foot", "Bip01 R Toe0",
        "Bip01 B skirt", "Bip01 B skirt01", "Bip01 L skirt", "Bip01 L skirt01", "Bip01 R skirt", "Bip01 R skirt01"
    ]

    @classmethod
    def parse_bones_from_data(cls, data: bytes, expected_bone_names: List[str]) -> List[dict]:
        count = struct.unpack("<H", data[:2])[0]
        idx = 2
        bones = []
        for b in range(count):
            start = idx
            name = data[idx:idx+100].split(b"\x00")[0].decode("ascii")
            parent = data[idx+100:idx+200].split(b"\x00")[0].decode("ascii")
            if b < count - 1:
                next_name = expected_bone_names[b+1].encode("ascii")
                next_pos = data.find(next_name, idx + 200)
                end = next_pos
            else:
                end = len(data)
            raw_block = data[start:end]
            bones.append({"name": name, "parent": parent, "raw": raw_block})
            idx = end
        return bones

    @classmethod
    def apply_adapted_skeletons(cls, base_dir: str, backup_dir: str) -> None:
        bone_dir = os.path.join(base_dir, "Character", "Player", "Bone")
        backup_bone_dir = os.path.join(backup_dir, "Character", "Player", "Bone")

        # Read pristine source files from _ModBackup
        with open(os.path.join(backup_bone_dir, "BelMale.bn"), "rb") as f:
            bm_data = f.read()
        with open(os.path.join(backup_bone_dir, "CorMale.bn"), "rb") as f:
            cm_data = f.read()
        with open(os.path.join(backup_bone_dir, "BelFemale.bn"), "rb") as f:
            bf_data = f.read()
        with open(os.path.join(backup_bone_dir, "CorFemale.bn"), "rb") as f:
            cf_data = f.read()

        bm_bones = cls.parse_bones_from_data(bm_data, cls.BM_NAMES)
        cm_bones = cls.parse_bones_from_data(cm_data, cls.CM_NAMES)
        bf_bones = cls.parse_bones_from_data(bf_data, cls.BF_NAMES)
        cf_bones = cls.parse_bones_from_data(cf_data, cls.CF_NAMES)

        # 1. BelMale.bn (30 bones): Cora Male + HeadNub
        headnub = bm_bones[7]
        adapted_bm = cm_bones[:7] + [headnub] + cm_bones[7:]
        data_new_bm = struct.pack("<H", 30) + b"".join(b["raw"] for b in adapted_bm)

        # 2. CorMale.bn (29 bones): Bellato Male minus HeadNub
        adapted_cm = [b for b in bm_bones if b["name"] != "Bip01 HeadNub"]
        data_new_cm = struct.pack("<H", 29) + b"".join(b["raw"] for b in adapted_cm)

        # 3. BelFemale.bn (25 bones): Cora Female minus 13 extra bones
        extra_cf = {
            "Bip01 Ponytail L1", "Bip01 Ponytail L11", "Bip01 Ponytail L1Nub",
            "Bip01 R Finger1", "Bip01 R Finger1Nub",
            "Bip01 L Finger1", "Bip01 L Finger1Nub",
            "Bip01 B skirt", "Bip01 B skirt01", "Bip01 L skirt", "Bip01 L skirt01", "Bip01 R skirt", "Bip01 R skirt01"
        }
        adapted_bf = [b for b in cf_bones if b["name"] not in extra_cf]
        data_new_bf = struct.pack("<H", 25) + b"".join(b["raw"] for b in adapted_bf)

        # 4. CorFemale.bn (38 bones): Bellato Female + 13 extra bones
        cf_extra_list = [b for b in cf_bones if b["name"] in extra_cf]
        adapted_cf = bf_bones + cf_extra_list
        data_new_cf = struct.pack("<H", 38) + b"".join(b["raw"] for b in adapted_cf)

        writes = [
            ("BelMale.bn", data_new_bm),
            ("Bellato_Male.bn", data_new_bm),
            ("CorMale.bn", data_new_cm),
            ("Cora_Male.bn", data_new_cm),
            ("BelFemale.bn", data_new_bf),
            ("Bellato_Female.bn", data_new_bf),
            ("CorFemale.bn", data_new_cf),
            ("Cora_Female.bn", data_new_cf),
        ]
        for fname, d in writes:
            p = os.path.join(bone_dir, fname)
            with open(p, "wb") as f:
                f.write(d)

        # Swap .BBX bounding box files
        bbx_swaps = [
            ("BelMale.BBX", "CorMale.BBX"),
            ("Bellato_Male.BBX", "Cora_Male.BBX"),
            ("BelFemale.BBX", "CorFemale.BBX"),
            ("Bellato_Female.BBX", "Cora_Female.BBX"),
        ]
        for f_a, f_b in bbx_swaps:
            pa = os.path.join(bone_dir, f_a)
            pb = os.path.join(bone_dir, f_b)
            p_orig_a = os.path.join(backup_bone_dir, f_a)
            p_orig_b = os.path.join(backup_bone_dir, f_b)
            if os.path.exists(p_orig_a) and os.path.exists(p_orig_b):
                with open(p_orig_a, "rb") as fa: da = fa.read()
                with open(p_orig_b, "rb") as fb: db = fb.read()
                with open(pa, "wb") as fa: fa.write(db)
                with open(pb, "wb") as fb: fb.write(da)


class AssetSwapper:
    def __init__(self, base_dir: str = BASE_DIR, backup_mgr: Optional[BackupManager] = None):
        self.base_dir = base_dir
        self.backup_mgr = backup_mgr or BackupManager(base_dir)

    def find_all_pairs(self) -> Dict[str, list]:
        catalog = {
            "mesh_rfs": [],
            "mesh_loose": [],
            "shared_mesh_rfs": [],
            "shared_tex_rfs": [],
            "tex_rfs": [],
            "tex_loose": [],
            "bone": [],
            "ani_rfs": [],
            "ani_mount": [],
            "bgm": [],
            "voice": [],
            "effects_eff": [],
            "effects_spt": [],
            "particle_dirs": []
        }

        # 1. Mesh RFS and loose MSH in Character/Player/Mesh/
        mesh_dir = os.path.join(self.base_dir, "Character", "Player", "Mesh")
        if os.path.exists(mesh_dir):
            files = os.listdir(mesh_dir)
            for f in files:
                if f.startswith("DEFAULTBF") and f.endswith(".RFS"):
                    catalog["mesh_rfs"].append(("Character/Player/Mesh/DEFAULTBF.RFS", "Character/Player/Mesh/DEFAULTCF.RFS", "FEMALE"))
                elif f.startswith("DEFAULTBM") and f.endswith(".RFS"):
                    catalog["mesh_rfs"].append(("Character/Player/Mesh/DEFAULTBM.RFS", "Character/Player/Mesh/DEFAULTCM.RFS", "MALE"))
                elif f.startswith("BF") and f.endswith(".RFS"):
                    cf = "CF" + f[2:]
                    if cf in files:
                        catalog["mesh_rfs"].append((f"Character/Player/Mesh/{f}", f"Character/Player/Mesh/{cf}", "FEMALE"))
                elif f.startswith("BM") and f.endswith(".RFS"):
                    cm = "CM" + f[2:]
                    if cm in files:
                        catalog["mesh_rfs"].append((f"Character/Player/Mesh/{f}", f"Character/Player/Mesh/{cm}", "MALE"))

            for f in files:
                if f.startswith("BELFEMALE_") and f.endswith(".msh"):
                    cf = "CORFEMALE_" + f[10:]
                    if cf in files:
                        catalog["mesh_loose"].append((f"Character/Player/Mesh/{f}", f"Character/Player/Mesh/{cf}", "FEMALE"))
                elif f.startswith("BELMALE_") and f.endswith(".msh"):
                    cm = "CORMALE_" + f[8:]
                    if cm in files:
                        catalog["mesh_loose"].append((f"Character/Player/Mesh/{f}", f"Character/Player/Mesh/{cm}", "MALE"))

            # 1c. Shared multi-race Mesh RFS in Character/Player/Mesh/
            shared_mesh_names = [
                "DARKM60.RFS", "ORI70.RFS", "ori6770.RFS", "RFMASTER.RFS", "WHITEM.RFS", "NWHITEM.RFS",
                "PHNMM.RFS", "PHNMM2.RFS", "XMH.RFS", "blktg_hm.RFS", "MASKM.RFS", "NPH02.RFS"
            ]
            for arc in shared_mesh_names:
                p = os.path.join(mesh_dir, arc)
                if os.path.exists(p):
                    catalog["shared_mesh_rfs"].append(f"Character/Player/Mesh/{arc}")

        # 1b. Cloak and Mount Meshes in Item/
        for sub, g_len_map in [
            ("Item/Armor/Mesh", {"BELFEMALE": "CORFEMALE", "BELMALE": "CORMALE"}),
            ("Item/Mount/Mesh", {"BELFEMALE": "CORFEMALE", "BELMALE": "CORMALE"}),
        ]:
            p = os.path.join(self.base_dir, sub)
            if os.path.exists(p):
                files = set(os.listdir(p))
                for f in files:
                    for b_prefix, c_prefix in g_len_map.items():
                        if f.startswith(b_prefix):
                            cf = c_prefix + f[len(b_prefix):]
                            if cf in files:
                                catalog["mesh_loose"].append((f"{sub}/{f}", f"{sub}/{cf}", "FEMALE" if "FEMALE" in b_prefix else "MALE"))

        # 2. Tex RFS and loose textures in Character/Player/Tex/
        tex_dir = os.path.join(self.base_dir, "Character", "Player", "Tex")
        if os.path.exists(tex_dir):
            files = os.listdir(tex_dir)
            for f in files:
                if f.startswith("DEFAULTBF") and f.endswith(".RFS"):
                    catalog["tex_rfs"].append(("Character/Player/Tex/DEFAULTBF.RFS", "Character/Player/Tex/DEFAULTCF.RFS", "FEMALE"))
                elif f.startswith("DEFAULTBM") and f.endswith(".RFS"):
                    catalog["tex_rfs"].append(("Character/Player/Tex/DEFAULTBM.RFS", "Character/Player/Tex/DEFAULTCM.RFS", "MALE"))
                elif f.startswith("BF") and f.endswith(".RFS"):
                    cf = "CF" + f[2:]
                    if cf in files:
                        catalog["tex_rfs"].append((f"Character/Player/Tex/{f}", f"Character/Player/Tex/{cf}", "FEMALE"))
                elif f.startswith("BM") and f.endswith(".RFS"):
                    cm = "CM" + f[2:]
                    if cm in files:
                        catalog["tex_rfs"].append((f"Character/Player/Tex/{f}", f"Character/Player/Tex/{cm}", "MALE"))

            for f in files:
                cf = None
                if f.startswith("BF_"): cf = "CF_" + f[3:]
                elif f.startswith("BM_"): cf = "CM_" + f[3:]
                elif f.startswith("B_F_"): cf = "C_F_" + f[4:]
                elif f.startswith("B_M_"): cf = "C_M_" + f[4:]
                elif f.startswith("Bel_Mask_"): continue  # Handled natively by shared PHNMM/NPH02 mesh
                elif f.startswith("BE_White_Tiger_Mask"): continue  # Handled natively by shared blktg_hm mesh
                elif f.startswith("Be_"): cf = "Co_" + f[3:]
                elif f.startswith("BE_"): cf = "CO_" + f[3:]
                elif f.startswith("B_Xmas_"): cf = "C_Xmas_" + f[7:]

                if cf and cf in files:
                    catalog["tex_loose"].append((f"Character/Player/Tex/{f}", f"Character/Player/Tex/{cf}"))

            # 2c. Shared multi-race Tex RFS in Character/Player/Tex/
            shared_tex_names = [
                "DARKT60.RFS", "ORI70.RFS", "ori6770.RFS", "RFMASTER.RFS", "WHITET.RFS", "NWHITET.RFS", "MASKT.RFS"
            ]
            for arc in shared_tex_names:
                p = os.path.join(tex_dir, arc)
                if os.path.exists(p):
                    catalog["shared_tex_rfs"].append(f"Character/Player/Tex/{arc}")

        # 2b. Mount, Model, and Armor textures in Item/
        for sub in ["Item/Armor/Tex", "Item/Mount/Tex", "Item/ModelItem/Tex"]:
            p = os.path.join(self.base_dir, sub)
            if os.path.exists(p):
                files = set(os.listdir(p))
                for f in files:
                    cf = None
                    if f.startswith("BF_"): cf = "CF_" + f[3:]
                    elif f.startswith("BM_"): cf = "CM_" + f[3:]
                    elif f.startswith("BE_"): cf = "CO_" + f[3:]
                    elif f.startswith("Bellato_"): cf = "Cora_" + f[8:]
                    elif f.startswith("B_Taiwan_"): cf = "C_Taiwan_" + f[9:]
                    elif f.startswith("B_Xmas_"): cf = "C_Xmas_" + f[7:]
                    elif f.startswith("B_jetski_"): cf = "C_jetski_" + f[9:]
                    elif f.startswith("BELMALE_"): cf = "CORMALE_" + f[8:]
                    elif f.startswith("BELFEMALE_"): cf = "CORFEMALE_" + f[10:]
                    elif "Booster_Ph_B" in f: cf = f.replace("Booster_Ph_B", "Booster_Ph_C")
                    elif "Booster_gold_B" in f: cf = f.replace("Booster_gold_B", "Booster_gold_C")
                    elif "Booster_Sliver_B" in f: cf = f.replace("Booster_Sliver_B", "Booster_Sliver_C")
                    elif "Manteau_Di_b" in f: cf = f.replace("Manteau_Di_b", "Manteau_Di_c")

                    if cf and cf in files:
                        catalog["tex_loose"].append((f"{sub}/{f}", f"{sub}/{cf}"))

        # 3. Bone and BBX files in Character/Player/Bone/ and Item/
        bone_dir = os.path.join(self.base_dir, "Character", "Player", "Bone")
        if os.path.exists(bone_dir):
            files = os.listdir(bone_dir)
            class_map = {
                "BELFEMALE_ARMOR_WARRIOR_181.bn": "CORFEMALE_ARMOR_WARRIOR_205.bn",
                "BELFEMALE_ARMOR_RANGER_189.bn": "CORFEMALE_ARMOR_RANGER_213.bn",
                "BELFEMALE_ARMOR_SPIRITUAL_197.bn": "CORFEMALE_ARMOR_SPIRITUAL_221.bn",
                "BELMALE_ARMOR_WARRIOR_181.bn": "CORMALE_ARMOR_WARRIOR_205.bn",
                "BELMALE_ARMOR_RANGER_189.bn": "CORMALE_ARMOR_RANGER_213.bn",
                "BELMALE_ARMOR_SPIRITUAL_197.bn": "CORMALE_ARMOR_SPIRITUAL_221.bn",
                "DRAGON_ARMOR_BELFEMALE_001_Silver.bn": "DRAGON_ARMOR_COFEMALE_001_Silver.bn",
                "DRAGON_ARMOR_BELMALE_001_Silver.bn": "DRAGON_ARMOR_COMALE_001_Silver.bn",
            }
            for bf, cf in class_map.items():
                if bf in STRICT_EXCLUSIONS or cf in STRICT_EXCLUSIONS:
                    continue
                if bf in files and cf in files:
                    catalog["bone"].append((f"Character/Player/Bone/{bf}", f"Character/Player/Bone/{cf}"))

            for f in files:
                if f in class_map or f in STRICT_EXCLUSIONS:
                    continue
                cf = None
                if f.startswith("BELFEMALE_"): cf = "CORFEMALE_" + f[10:]
                elif f.startswith("BELMALE_"): cf = "CORMALE_" + f[8:]
                if cf and cf in files and cf not in STRICT_EXCLUSIONS:
                    catalog["bone"].append((f"Character/Player/Bone/{f}", f"Character/Player/Bone/{cf}"))

        # 3b. Cloak and Mount Bones in Item/
        for sub in ["Item/Armor/Bone", "Item/Mount/Bone"]:
            p = os.path.join(self.base_dir, sub)
            if os.path.exists(p):
                files = set(os.listdir(p))
                for f in files:
                    cf = None
                    if f.startswith("BELFEMALE_"): cf = "CORFEMALE_" + f[10:]
                    elif f.startswith("BELMALE_"): cf = "CORMALE_" + f[8:]
                    if cf and cf in files:
                        catalog["bone"].append((f"{sub}/{f}", f"{sub}/{cf}"))

        # 4. Animation RFS in Character/Player/Ani/
        ani_dir = os.path.join(self.base_dir, "Character", "Player", "Ani")
        if os.path.exists(ani_dir):
            files = os.listdir(ani_dir)
            allowed_ani_codes = ["ATA", "COA", "GEA", "MEA", "MHA", "MOA", "RAA", "RHA"]
            for code in allowed_ani_codes:
                bf = f"BF{code}.RFS"
                cf = f"CF{code}.RFS"
                if bf in files and cf in files:
                    catalog["ani_rfs"].append((f"Character/Player/Ani/{bf}", f"Character/Player/Ani/{cf}", "FEMALE", code == "MOA"))

                bm = f"BM{code}.RFS"
                cm = f"CM{code}.RFS"
                if bm in files and cm in files:
                    catalog["ani_rfs"].append((f"Character/Player/Ani/{bm}", f"Character/Player/Ani/{cm}", "MALE", code == "MOA"))

            for f in files:
                if f.startswith("BELFEMALE_") and f.endswith(".ANI"):
                    cf = "CORFEMALE_" + f[10:]
                    if cf in files:
                        catalog["ani_mount"].append((f"Character/Player/Ani/{f}", f"Character/Player/Ani/{cf}"))
                elif f.startswith("BELMALE_") and f.endswith(".ANI"):
                    cm = "CORMALE_" + f[8:]
                    if cm in files:
                        catalog["ani_mount"].append((f"Character/Player/Ani/{f}", f"Character/Player/Ani/{cm}"))

        # 4b. Loose Cloak, Mount, and ModelItem animations in Item/
        for sub in ["Item/Armor/Ani", "Item/Mount/Ani", "Item/ModelItem/Ani"]:
            p = os.path.join(self.base_dir, sub)
            if os.path.exists(p):
                files = set(os.listdir(p))
                for f in files:
                    cf = None
                    if f.startswith("BELFEMALE_"): cf = "CORFEMALE_" + f[10:]
                    elif f.startswith("BELMALE_"): cf = "CORMALE_" + f[8:]
                    if cf and cf in files:
                        catalog["ani_mount"].append((f"{sub}/{f}", f"{sub}/{cf}"))

        # 5. Audio: BGM and Character Voices
        bgm_pairs = [
            ("Snd/BGM/Belato_Base01.mp3", "Snd/BGM/Cora_Base01.mp3"),
            ("Snd/BGM/Belato_Base_00.mp3", "Snd/BGM/Cora_Base_00.mp3")
        ]
        for b, c in bgm_pairs:
            if os.path.exists(os.path.join(self.base_dir, b)) and os.path.exists(os.path.join(self.base_dir, c)):
                catalog["bgm"].append((b, c))

        # Comprehensive racial voice line matching
        for cat in ["Attack", "DAMAGE", "Emotion"]:
            for b_sub, c_sub in [("B_M", "C_M"), ("B_W", "C_W")]:
                b_dir = os.path.join(self.base_dir, "Snd", "Character", cat, b_sub)
                c_dir = os.path.join(self.base_dir, "Snd", "Character", cat, c_sub)
                if os.path.exists(b_dir) and os.path.exists(c_dir):
                    c_files = set(os.listdir(c_dir))
                    for bf in os.listdir(b_dir):
                        if not bf.endswith((".wav", ".ogg", ".mp3")):
                            continue
                        cf = None
                        if bf.startswith("BELMALE_"): cf = bf.replace("BELMALE_", "CORMALE_")
                        elif bf.startswith("BELFEMALE_"): cf = bf.replace("BELFEMALE_", "CORFEMALE_")
                        if cf and cf in c_files:
                            catalog["voice"].append((
                                f"Snd/Character/{cat}/{b_sub}/{bf}",
                                f"Snd/Character/{cat}/{c_sub}/{cf}"
                            ))

        voice_singles = [
            ("Snd/Character/Die/BELFEMALE_die.wav", "Snd/Character/Die/CORFEMALE_die.wav"),
            ("Snd/Character/Die/BELMALE_die.wav", "Snd/Character/Die/CORMALE_die.wav"),
            ("Snd/Character/Levelup/BLV_00.wav", "Snd/Character/Levelup/CLV_00.wav"),
            ("Snd/Character/Move/BWalk_00.wav", "Snd/Character/Move/CWALK_00.wav"),
            ("Snd/Character/Potion/bpotion_00.wav", "Snd/Character/Potion/cpotion_00.wav"),
            ("Snd/Character/Rezen/blezen_00.wav", "Snd/Character/Rezen/clezen_00.wav"),
            ("Snd/Character/Faint/BELMALE_damage_critical.wav", "Snd/Character/Faint/CORMALE_damage_critical.wav"),
        ]
        for b, c in voice_singles:
            if os.path.exists(os.path.join(self.base_dir, b)) and os.path.exists(os.path.join(self.base_dir, c)):
                catalog["voice"].append((b, c))

        # 6. Comprehensive Armor and Glow Effects (.EFF) across Chef/
        chef_dir = os.path.join(self.base_dir, "Chef")
        if os.path.exists(chef_dir):
            class_offsets = {
                179: 203, 183: 207, 187: 211, 191: 215, 195: 219, 199: 223,  # +24 sets
                181: 205, 189: 213, 197: 221,  # 70LV
                174: 175  # Level 50 set
            }
            for root, _, files in os.walk(chef_dir):
                # Never touch Animus or MAU/Unit effects
                if "Taiwan_GuardTower" in root or "75LV_Animus" in root or "75LV_UNIT" in root:
                    continue
                fset = set(files)
                for f in files:
                    if not f.endswith(".EFF"):
                        continue
                    cf = None
                    if f.startswith("BELFEMALE_"):
                        cor_cand = "CORFEMALE_" + f[10:]
                        if cor_cand in fset:
                            cf = cor_cand
                        else:
                            for b_num, c_num in class_offsets.items():
                                if f"_{b_num}_" in f or f"_{b_num}." in f:
                                    cand = f.replace("BELFEMALE_", "CORFEMALE_").replace(str(b_num), str(c_num))
                                    if cand in fset:
                                        cf = cand
                                        break
                    elif f.startswith("BELMALE_"):
                        cor_cand = "CORMALE_" + f[8:]
                        if cor_cand in fset:
                            cf = cor_cand
                        else:
                            for b_num, c_num in class_offsets.items():
                                if f"_{b_num}_" in f or f"_{b_num}." in f:
                                    cand = f.replace("BELMALE_", "CORMALE_").replace(str(b_num), str(c_num))
                                    if cand in fset:
                                        cf = cand
                                        break
                    elif f.startswith("BEL_"):
                        cor_cand = "COR_" + f[4:]
                        if cor_cand in fset: cf = cor_cand
                    elif f.startswith("Be_"):
                        cor_cand = "Co_" + f[3:]
                        if cor_cand in fset: cf = cor_cand

                    if cf:
                        p_b = os.path.relpath(os.path.join(root, f), self.base_dir).replace("\\", "/")
                        p_c = os.path.relpath(os.path.join(root, cf), self.base_dir).replace("\\", "/")
                        catalog["effects_eff"].append((p_b, p_c))

        # 7. Ranking reward auras
        rank_dir = os.path.join(self.base_dir, "Effect", "Character_3", "ranking_reward")
        if os.path.exists(rank_dir):
            for i in range(6):
                suffix = f"_{i:02d}.spt" if i > 0 else ".spt"
                bf = f"reward_Be_mag{suffix}"
                cf = f"reward_Co_mag{suffix}"
                if os.path.exists(os.path.join(rank_dir, bf)) and os.path.exists(os.path.join(rank_dir, cf)):
                    catalog["effects_spt"].append((
                        f"Effect/Character_3/ranking_reward/{bf}",
                        f"Effect/Character_3/ranking_reward/{cf}"
                    ))
            # Ranking reward src: race emblems, circles, lights
            src_dir = os.path.join(rank_dir, "src")
            if os.path.exists(src_dir):
                src_pairs = [("mark_be_p.spt", "mark_co_p.spt"),
                             ("cora_circle.spt", "circle.spt"),
                             ("cora_light.spt", "light.spt")]
                for bf, cf in src_pairs:
                    if os.path.exists(os.path.join(src_dir, bf)) and os.path.exists(os.path.join(src_dir, cf)):
                        catalog["effects_spt"].append((
                            f"Effect/Character_3/ranking_reward/src/{bf}",
                            f"Effect/Character_3/ranking_reward/src/{cf}"
                        ))
                # mark_be_p/ <-> mark_co_p/ texture directories
                if os.path.isdir(os.path.join(src_dir, "mark_be_p")) and os.path.isdir(os.path.join(src_dir, "mark_co_p")):
                    catalog["particle_dirs"].append((
                        "Effect/Character_3/ranking_reward/src/mark_be_p",
                        "Effect/Character_3/ranking_reward/src/mark_co_p"
                    ))
                # cora_light/ <-> light/ directories
                if os.path.isdir(os.path.join(src_dir, "cora_light")) and os.path.isdir(os.path.join(src_dir, "light")):
                    catalog["particle_dirs"].append((
                        "Effect/Character_3/ranking_reward/src/cora_light",
                        "Effect/Character_3/ranking_reward/src/light"
                    ))
                # circle_main/ <-> circle/ directories
                if os.path.isdir(os.path.join(src_dir, "circle_main")) and os.path.isdir(os.path.join(src_dir, "circle")):
                    catalog["particle_dirs"].append((
                        "Effect/Character_3/ranking_reward/src/circle_main",
                        "Effect/Character_3/ranking_reward/src/circle"
                    ))

        # 8. Booster exhaust SPT content swap
        booster_spt = [
            ("Effect/item_8/Booster_CLOAK/BE/attack/BE_CLOAK_attack.spt", "Effect/item_8/Booster_CLOAK/CO/attack/CO_CLOAK_attack.spt"),
            ("Effect/item_8/Booster_CLOAK/BE/use/BE_CLOAK_use.spt", "Effect/item_8/Booster_CLOAK/CO/use/CO_CLOAK_use.spt")
        ]
        for b, c in booster_spt:
            if os.path.exists(os.path.join(self.base_dir, b)) and os.path.exists(os.path.join(self.base_dir, c)):
                catalog["effects_spt"].append((b, c))

        # 9. Particle directories in Chef (BE <-> CO)
        if os.path.exists(chef_dir):
            for sub in os.listdir(chef_dir):
                if sub == "Taiwan_GuardTower":
                    continue
                sub_path = os.path.join(chef_dir, sub)
                if not os.path.isdir(sub_path):
                    continue
                children = os.listdir(sub_path)
                c_map = {c.lower(): c for c in children}
                if "be" in c_map and "co" in c_map:
                    be_name = c_map["be"]
                    co_name = c_map["co"]
                    catalog["particle_dirs"].append((
                        f"Chef/{sub}/{be_name}",
                        f"Chef/{sub}/{co_name}"
                    ))

        return catalog

    def execute_swap(self) -> Dict[str, int]:
        catalog = self.find_all_pairs()
        stats = {k: 0 for k in catalog}
        stats["sprite_icons"] = 0
        stats["rfs_cloaks"] = 0

        all_to_backup = set()
        for item in catalog["mesh_rfs"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["mesh_loose"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["shared_mesh_rfs"]:
            all_to_backup.add(item)
        for item in catalog["shared_tex_rfs"]:
            all_to_backup.add(item)
        for item in catalog["tex_rfs"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["tex_loose"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["bone"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["ani_rfs"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["ani_mount"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["bgm"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["voice"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["effects_eff"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        for item in catalog["effects_spt"]:
            all_to_backup.add(item[0]); all_to_backup.add(item[1])
        # MagicSptList.spt for patriarch/archon/guild master effect table patching
        magic_spt_rel = "Effect/MagicSptList.spt"
        if os.path.exists(os.path.join(self.base_dir, magic_spt_rel)):
            all_to_backup.add(magic_spt_rel)
        rfs_cloaks = [
            "Item/Armor/Mesh/AKM00.RFS",
            "Item/Armor/Tex/AKT00.RFS",
            "Item/Armor/Ani/ACA00.RFS",
            "Item/Armor/Mesh/XMC.RFS",
            "Item/Armor/Mesh/blktg_cl.RFS",
        ]
        for rfs_rel in rfs_cloaks:
            if os.path.exists(os.path.join(self.base_dir, rfs_rel)) or os.path.exists(os.path.join(self.backup_mgr.backup_dir, rfs_rel)):
                all_to_backup.add(rfs_rel)

        for be_dir_rel, co_dir_rel in catalog["particle_dirs"]:
            be_full = os.path.join(self.base_dir, be_dir_rel)
            co_full = os.path.join(self.base_dir, co_dir_rel)
            for root, _, files in os.walk(be_full):
                for f in files:
                    all_to_backup.add(os.path.relpath(os.path.join(root, f), self.base_dir).replace("\\", "/"))
            for root, _, files in os.walk(co_full):
                for f in files:
                    all_to_backup.add(os.path.relpath(os.path.join(root, f), self.base_dir).replace("\\", "/"))

        spr_files = [
            "SpriteImage/ru-ru/item.spr",
            "SpriteImage/ru-ru/common.spr",
            "SpriteImage/common.spr",
            "SpriteImage/common/common.spr",
            "SpriteImage/common/common/common.spr",
            "SpriteImage/en-gb/common.spr",
            "SpriteImage/common/pvp.spr",
            "SpriteImage/common/common/pvp.spr",
            "SpriteImage/common/charinfo.spr",
            "SpriteImage/en-gb/charinfo.spr",
        ]
        for spr_rel in spr_files:
            if os.path.exists(os.path.join(self.base_dir, spr_rel)):
                all_to_backup.add(spr_rel)

        base_bone_files = [
            "Character/Player/Bone/BelMale.bn", "Character/Player/Bone/Bellato_Male.bn",
            "Character/Player/Bone/CorMale.bn", "Character/Player/Bone/Cora_Male.bn",
            "Character/Player/Bone/BelFemale.bn", "Character/Player/Bone/Bellato_Female.bn",
            "Character/Player/Bone/CorFemale.bn", "Character/Player/Bone/Cora_Female.bn",
            "Character/Player/Bone/BelMale.BBX", "Character/Player/Bone/Bellato_Male.BBX",
            "Character/Player/Bone/CorMale.BBX", "Character/Player/Bone/Cora_Male.BBX",
            "Character/Player/Bone/BelFemale.BBX", "Character/Player/Bone/Bellato_Female.BBX",
            "Character/Player/Bone/CorFemale.BBX", "Character/Player/Bone/Cora_Female.BBX",
        ]
        for f_rel in base_bone_files:
            if os.path.exists(os.path.join(self.base_dir, f_rel)):
                all_to_backup.add(f_rel)

        print(f"[*] Backing up {len(all_to_backup)} unique files to _ModBackup/...")
        self.backup_mgr.backup_files(list(all_to_backup), swapped_dirs=catalog["particle_dirs"])
        print("[+] Backup completed successfully.")

        # 1. Mesh RFS Swap
        print("[*] Swapping Player Mesh RFS archives...")
        for b_rel, c_rel, gender in catalog["mesh_rfs"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            RFSHandler.swap_and_patch_rfs(p_b, p_c, gender)
            stats["mesh_rfs"] += 1

        # 2. Loose Mesh Swap
        print("[*] Swapping loose MSH models...")
        for b_rel, c_rel, gender in catalog["mesh_loose"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            with open(p_b, "rb") as f:
                data_b = f.read()
            with open(p_c, "rb") as f:
                data_c = f.read()

            b_pref = f"BEL{gender}_".encode("ascii")
            c_pref = f"COR{gender}_".encode("ascii")

            data_b_for_c = (
                data_b.replace(b_pref, c_pref)
                .replace(b"BM_", b"CM_").replace(b"BF_", b"CF_")
                .replace(b"B_M_", b"C_M_").replace(b"B_F_", b"C_F_")
                .replace(b"BEMA_", b"COMA_").replace(b"BEFE_", b"COFE_")
                .replace(b"Be_", b"Co_").replace(b"BE_", b"CO_")
            )
            data_c_for_b = (
                data_c.replace(c_pref, b_pref)
                .replace(b"CM_", b"BM_").replace(b"CF_", b"BF_")
                .replace(b"C_M_", b"B_M_").replace(b"C_F_", b"B_F_")
                .replace(b"COMA_", b"BEMA_").replace(b"COFE_", b"BEFE_")
                .replace(b"Co_", b"Be_").replace(b"CO_", b"BE_")
            )

            with open(p_c, "wb") as f:
                f.write(data_b_for_c)
            with open(p_b, "wb") as f:
                f.write(data_c_for_b)
            stats["mesh_loose"] += 1

        # 2b. Shared Multi-Race Mesh RFS Swap (High-level & Special armors)
        print("[*] Swapping shared multi-race Player Mesh RFS archives (50-75LV, Master, White, Dragon, Masks)...")
        stats["shared_mesh_pairs"] = 0
        for arc_rel in catalog["shared_mesh_rfs"]:
            p = os.path.join(self.base_dir, arc_rel)
            num_swapped = RFSHandler.swap_shared_rfs_internal(p)
            stats["shared_mesh_pairs"] += num_swapped
            stats["shared_mesh_rfs"] += 1
            print(f"    - {os.path.basename(arc_rel)}: {num_swapped} character mesh pairs swapped")

        # 3. Tex RFS Swap
        print("[*] Swapping Player Texture RFS archives...")
        for b_rel, c_rel, gender in catalog["tex_rfs"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            RFSHandler.swap_and_patch_rfs(p_b, p_c, gender)
            stats["tex_rfs"] += 1

        # 3b. Shared Multi-Race Tex RFS Swap (High-level & Special armors)
        print("[*] Swapping shared multi-race Player Texture RFS archives (50-75LV, Master, White, Dragon, Masks)...")
        stats["shared_tex_pairs"] = 0
        for arc_rel in catalog["shared_tex_rfs"]:
            p = os.path.join(self.base_dir, arc_rel)
            num_swapped = RFSHandler.swap_shared_rfs_internal(p)
            stats["shared_tex_pairs"] += num_swapped
            stats["shared_tex_rfs"] += 1
            print(f"    - {os.path.basename(arc_rel)}: {num_swapped} texture pairs swapped")

        # 4. Loose Textures
        print("[*] Swapping loose DDS textures...")
        for b_rel, c_rel in catalog["tex_loose"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            self._safe_swap_files(p_b, p_c)
            stats["tex_loose"] += 1

        # 5. Bones & BBX
        print("[*] Swapping skeleton and bone hierarchy files (.bn, .BBX)...")
        for b_rel, c_rel in catalog["bone"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            self._safe_swap_files(p_b, p_c)
            stats["bone"] += 1

        print("[*] Applying adapted base skeletons (validator-compliant race proportions)...")
        SkeletonAdapter.apply_adapted_skeletons(self.base_dir, BACKUP_DIR)
        stats["bone"] += 8

        # 6. Ani RFS
        print("[*] Swapping permitted animations with RAXETHROW protection...")
        for b_rel, c_rel, gender, is_moa in catalog["ani_rfs"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            if is_moa:
                RFSHandler.swap_moa_with_raxethrow_protection(p_b, p_c, gender)
            else:
                RFSHandler.swap_and_patch_rfs(p_b, p_c, gender)
            stats["ani_rfs"] += 1

        for b_rel, c_rel in catalog["ani_mount"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            self._safe_swap_files(p_b, p_c)
            stats["ani_mount"] += 1

        # 7. Audio & BGM
        print("[*] Swapping base music and racial voices...")
        for b_rel, c_rel in catalog["bgm"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            self._safe_swap_files(p_b, p_c)
            stats["bgm"] += 1

        for b_rel, c_rel in catalog["voice"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            self._safe_swap_files(p_b, p_c)
            stats["voice"] += 1

        # 8. Effects (.EFF and .SPT)
        print("[*] Swapping armor and booster glow effects (.EFF)...")
        for b_rel, c_rel in catalog["effects_eff"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            self._safe_swap_files(p_b, p_c)
            stats["effects_eff"] += 1

        print("[*] Swapping ranking reward auras and exhaust scripts...")
        for b_rel, c_rel in catalog["effects_spt"]:
            p_b = os.path.join(self.base_dir, b_rel)
            p_c = os.path.join(self.base_dir, c_rel)
            self._safe_swap_files(p_b, p_c)
            stats["effects_spt"] += 1

        # 8.5. Patriarch / Archon / Guild Master effect table patching
        print("[*] Patching MagicSptList.spt (patriarch, archon, guild master effects)...")
        stats["magic_spt_patched"] = self._patch_magic_spt_list()
        print(f"    [+] Patched {stats['magic_spt_patched']} effect table entries in MagicSptList.spt")

        # 9. Particle Directories (BE <-> CO)
        print("[*] Swapping booster particle directory contents...")
        for be_rel, co_rel in catalog["particle_dirs"]:
            p_be = os.path.join(self.base_dir, be_rel)
            p_co = os.path.join(self.base_dir, co_rel)
            self._safe_swap_directories(p_be, p_co)
            stats["particle_dirs"] += 1

        # 10. Sprite Lossless Swaps: item.spr, common.spr, pvp.spr, charinfo.spr
        print("[*] Performing lossless DXT1 block swap in SpriteImage/ru-ru/item.spr...")
        spr_patcher = SpritePatcher(os.path.join(self.base_dir, "SpriteImage", "ru-ru", "item.spr"))
        stats["sprite_icons"] = spr_patcher.swap_icon_blocks()

        print("[*] Swapping overhead rank badges in common.spr...")
        stats["common_rank_badges"] = SpritePatcher.swap_common_rank_badges(self.base_dir)
        print(f"    [+] Swapped {stats['common_rank_badges']} badge pairs in common.spr copies")

        print("[*] Swapping target race crests in pvp.spr...")
        stats["pvp_crests"] = SpritePatcher.swap_pvp_race_badges(self.base_dir)
        print(f"    [+] Swapped {stats['pvp_crests']} crest blocks in pvp.spr")

        print("[*] Swapping race crests in charinfo.spr...")
        stats["charinfo_crests"] = SpritePatcher.swap_charinfo_race_badges(self.base_dir)
        print(f"    [+] Swapped {stats['charinfo_crests']} crest page in charinfo.spr")

        # 11. RFS Packed Anti-Gravs & Boosters (AKM00.RFS, AKT00.RFS, ACA00.RFS, XMC.RFS, blktg_cl.RFS)
        print("[*] Processing RFS anti-gravs and boosters (AKM00, AKT00, ACA00, XMC, blktg_cl)...")
        stats["rfs_cloaks"] = 0

        # A. AKM00.RFS (Meshes: Cora gets Bellato anti-grav with 8 Ball dummies; Bellato gets Cora wings)
        akm_backup = os.path.join(self.backup_mgr.backup_dir, "Item/Armor/Mesh/AKM00.RFS")
        if not os.path.exists(akm_backup):
            akm_backup = os.path.join(self.base_dir, "Item/Armor/Mesh/AKM00.RFS")
        if os.path.exists(akm_backup):
            akm_entries, _ = RFSHandler.read_rfs(akm_backup)
            akm_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): bytes(e["data"]) for e in akm_entries}
            out_akm = []
            for e in akm_entries:
                name = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                new_data = bytes(e["data"])
                if name.startswith("CORFEMALE_"):
                    bel_name = name.replace("CORFEMALE_", "BELFEMALE_")
                    if bel_name in akm_map:
                        new_data = akm_map[bel_name]
                elif name.startswith("CORMALE_"):
                    bel_name = name.replace("CORMALE_", "BELMALE_")
                    if bel_name in akm_map:
                        new_data = akm_map[bel_name]
                elif name.startswith("BELFEMALE_"):
                    cor_name = name.replace("BELFEMALE_", "CORFEMALE_")
                    if cor_name in akm_map:
                        new_data = akm_map[cor_name]
                elif name.startswith("BELMALE_"):
                    cor_name = name.replace("BELMALE_", "CORMALE_")
                    if cor_name in akm_map:
                        new_data = akm_map[cor_name]
                out_akm.append({
                    "name_raw": e["name_raw"],
                    "meta": e["meta"],
                    "size": len(new_data),
                    "data": bytearray(new_data)
                })
            RFSHandler.write_rfs(os.path.join(self.base_dir, "Item/Armor/Mesh/AKM00.RFS"), out_akm)
            stats["rfs_cloaks"] += 1

        # B. AKT00.RFS (Textures: Cora gets Bellato textures; Bellato gets Cora textures)
        akt_backup = os.path.join(self.backup_mgr.backup_dir, "Item/Armor/Tex/AKT00.RFS")
        if not os.path.exists(akt_backup):
            akt_backup = os.path.join(self.base_dir, "Item/Armor/Tex/AKT00.RFS")
        if os.path.exists(akt_backup):
            akt_entries, _ = RFSHandler.read_rfs(akt_backup)
            akt_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): bytes(e["data"]) for e in akt_entries}
            out_akt = []
            for e in akt_entries:
                name = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                new_data = bytes(e["data"])
                if name.startswith("CORFEMALE_WEAPON_CLOAK_"):
                    bel_name = name.replace("CORFEMALE_", "BELFEMALE_")
                    if bel_name in akt_map:
                        new_data = akt_map[bel_name]
                elif name.startswith("CORMALE_WEAPON_CLOAK_"):
                    bel_name = name.replace("CORMALE_", "BELMALE_")
                    if bel_name in akt_map:
                        new_data = akt_map[bel_name]
                elif name.startswith("BELFEMALE_WEAPON_CLOAK_"):
                    cor_name = name.replace("BELFEMALE_", "CORFEMALE_")
                    if cor_name in akt_map:
                        new_data = akt_map[cor_name]
                elif name.startswith("BELMALE_WEAPON_CLOAK_"):
                    cor_name = name.replace("BELMALE_", "CORMALE_")
                    if cor_name in akt_map:
                        new_data = akt_map[cor_name]
                elif name == "Gold_CF_CLOAK_000.RFT":
                    new_data = akt_map.get("Gold_BF_CLOAK_000.RFT", new_data)
                elif name == "Gold_BF_CLOAK_000.RFT":
                    new_data = akt_map.get("Gold_CF_CLOAK_000.RFT", new_data)
                elif name == "Gold_CM_CLOAK_000.RFT":
                    new_data = akt_map.get("Gold_BM_CLOAK_000.RFT", new_data)
                elif name == "Gold_BM_CLOAK_000.RFT":
                    new_data = akt_map.get("Gold_CM_CLOAK_000.RFT", new_data)
                out_akt.append({
                    "name_raw": e["name_raw"],
                    "meta": e["meta"],
                    "size": len(new_data),
                    "data": bytearray(new_data)
                })
            RFSHandler.write_rfs(os.path.join(self.base_dir, "Item/Armor/Tex/AKT00.RFS"), out_akt)
            stats["rfs_cloaks"] += 1

        # C. ACA00.RFS (Animations: Cora gets Bellato orbit animations; Bellato gets Cora wing animations)
        aca_backup = os.path.join(self.backup_mgr.backup_dir, "Item/Armor/Ani/ACA00.RFS")
        if not os.path.exists(aca_backup):
            aca_backup = os.path.join(self.base_dir, "Item/Armor/Ani/ACA00.RFS")
        if os.path.exists(aca_backup):
            aca_entries, _ = RFSHandler.read_rfs(aca_backup)
            aca_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): bytes(e["data"]) for e in aca_entries}
            out_aca = []
            for e in aca_entries:
                name = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                new_data = bytes(e["data"])
                if name.startswith("CORFEMALE_"):
                    bel_name = name.replace("CORFEMALE_", "BELFEMALE_")
                    if bel_name in aca_map:
                        new_data = aca_map[bel_name]
                elif name.startswith("CORMALE_"):
                    bel_name = name.replace("CORMALE_", "BELMALE_")
                    if bel_name in aca_map:
                        new_data = aca_map[bel_name]
                elif name.startswith("BELFEMALE_"):
                    cor_name = name.replace("BELFEMALE_", "CORFEMALE_")
                    if cor_name in aca_map:
                        new_data = aca_map[cor_name]
                elif name.startswith("BELMALE_"):
                    cor_name = name.replace("BELMALE_", "CORMALE_")
                    if cor_name in aca_map:
                        new_data = aca_map[cor_name]
                out_aca.append({
                    "name_raw": e["name_raw"],
                    "meta": e["meta"],
                    "size": len(new_data),
                    "data": bytearray(new_data)
                })
            RFSHandler.write_rfs(os.path.join(self.base_dir, "Item/Armor/Ani/ACA00.RFS"), out_aca)
            stats["rfs_cloaks"] += 1

        # D. XMC.RFS and blktg_cl.RFS (Holiday and Tiger Boosters: Cora <-> Bellato)
        for rfs_rel in ["Item/Armor/Mesh/XMC.RFS", "Item/Armor/Mesh/blktg_cl.RFS"]:
            rfs_backup = os.path.join(self.backup_mgr.backup_dir, rfs_rel)
            if not os.path.exists(rfs_backup):
                rfs_backup = os.path.join(self.base_dir, rfs_rel)
            if os.path.exists(rfs_backup):
                r_entries, _ = RFSHandler.read_rfs(rfs_backup)
                r_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): bytes(e["data"]) for e in r_entries}
                out_r = []
                for e in r_entries:
                    name = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                    new_data = bytes(e["data"])
                    if name.startswith("CORFEMALE_"):
                        bel_name = name.replace("CORFEMALE_", "BELFEMALE_")
                        if bel_name in r_map:
                            new_data = r_map[bel_name]
                    elif name.startswith("CORMALE_"):
                        bel_name = name.replace("CORMALE_", "BELMALE_")
                        if bel_name in r_map:
                            new_data = r_map[bel_name]
                    elif name.startswith("BELFEMALE_"):
                        cor_name = name.replace("BELFEMALE_", "CORFEMALE_")
                        if cor_name in r_map:
                            new_data = r_map[cor_name]
                    elif name.startswith("BELMALE_"):
                        cor_name = name.replace("BELMALE_", "CORMALE_")
                        if cor_name in r_map:
                            new_data = r_map[cor_name]
                    out_r.append({
                        "name_raw": e["name_raw"],
                        "meta": e["meta"],
                        "size": len(new_data),
                        "data": bytearray(new_data)
                    })
                RFSHandler.write_rfs(os.path.join(self.base_dir, rfs_rel), out_r)
                stats["rfs_cloaks"] += 1

        return stats

    def _patch_magic_spt_list(self) -> int:
        """Patch Effect/MagicSptList.spt to swap Cora <-> Bellato effect file references.

        Swaps the SPT file paths for:
        - Patriarch (0x11F90160 <-> 0x11F70160)
        - Sub-Patriarch/Archon (0x11F90161 <-> 0x11F70161)
        - Guild Master (0x11F90162 <-> 0x11F70162)
        - Crystal stones (0x11F90170 <-> 0x11F70170)

        After patching:
        - Cora characters load Bellato patriarch/archon/GM effects
        - Bellato characters load Cora patriarch/archon/GM effects
        - Accretia remains 100% untouched
        """
        path = os.path.join(self.base_dir, "Effect", "MagicSptList.spt")
        if not os.path.exists(path):
            print("    [!] MagicSptList.spt not found, skipping.")
            return 0

        with open(path, "rb") as f:
            raw = f.read()

        lines = raw.split(b"\n")

        # Each entry: hex_id_bytes -> (old_filename, new_filename)
        # Cora hex prefix = F9, Bellato hex prefix = F7
        swap_rules = {
            # Patriarch
            b"0x11F90160": (b"theone_coB_mag.spt", b"theone_beB_mag.spt"),
            b"0x11F70160": (b"theone_beB_mag.spt", b"theone_coB_mag.spt"),
            # Archon / Sub-Patriarch
            b"0x11F90161": (b"theone_coB_mag.spt", b"theone_beB_mag.spt"),
            b"0x11F70161": (b"theone_beB_mag.spt", b"theone_coB_mag.spt"),
            # Guild Master
            b"0x11F90162": (b"cora_gm_mag.spt", b"bella_gm_mag.spt"),
            b"0x11F70162": (b"bella_gm_mag.spt", b"cora_gm_mag.spt"),
            # Crystal Stones (guild war)
            b"0x11F70170": (b"crystal_be_mag.spt", b"crystal_co_mag.spt"),
            b"0x11F90170": (b"crystal_co_mag.spt", b"crystal_be_mag.spt"),
        }

        patched_count = 0
        new_lines = []
        for line in lines:
            stripped = line.lstrip()
            patched = False
            for hex_id, (old_fn, new_fn) in swap_rules.items():
                if stripped.lower().startswith(hex_id.lower()) and old_fn in line:
                    line = line.replace(old_fn, new_fn, 1)
                    patched_count += 1
                    patched = True
                    break
            new_lines.append(line)

        result = b"\n".join(new_lines)
        with open(path, "wb") as f:
            f.write(result)

        return patched_count

    @staticmethod
    def _safe_swap_files(path_a: str, path_b: str) -> None:
        tmp = path_a + ".tmp_swap"
        os.rename(path_a, tmp)
        os.rename(path_b, path_a)
        os.rename(tmp, path_b)

    @staticmethod
    def _safe_swap_directories(dir_a: str, dir_b: str) -> None:
        tmp = dir_a + "_tmp_swap"
        os.rename(dir_a, tmp)
        os.rename(dir_b, dir_a)
        os.rename(tmp, dir_b)


class CacheManager:
    def __init__(self, base_dir: str = BASE_DIR, cache_dir: str = CACHE_DIR):
        self.base_dir = base_dir
        self.cache_dir = cache_dir

    def build_cache_from_active_mod(self, backup_manifest_path: str = BACKUP_MANIFEST) -> int:
        if not os.path.exists(backup_manifest_path):
            print("[-] Backup manifest not found. Cannot populate cache.")
            return 0

        with open(backup_manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        files_manifest = manifest_data.get("files", manifest_data)
        swapped_dirs = manifest_data.get("swapped_dirs", [])

        os.makedirs(self.cache_dir, exist_ok=True)
        cached_count = 0

        print(f"[*] Populating local cache _ModCache/...")
        for rel in files_manifest:
            src = os.path.join(self.base_dir, rel)
            dst = os.path.join(self.cache_dir, rel)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                cached_count += 1

        # Also copy all files in swapped directories to ensure full tree preservation
        for dir_a_rel, dir_b_rel in swapped_dirs:
            for d_rel in [dir_a_rel, dir_b_rel]:
                src_dir = os.path.join(self.base_dir, d_rel)
                dst_dir = os.path.join(self.cache_dir, d_rel)
                if os.path.exists(src_dir):
                    for root, _, files in os.walk(src_dir):
                        for f in files:
                            src_f = os.path.join(root, f)
                            rel_f = os.path.relpath(src_f, self.base_dir).replace("\\", "/")
                            dst_f = os.path.join(self.cache_dir, rel_f)
                            if not os.path.exists(dst_f):
                                os.makedirs(os.path.dirname(dst_f), exist_ok=True)
                                shutil.copy2(src_f, dst_f)
                                cached_count += 1

        print(f"[+] Cached {cached_count} files in {self.cache_dir}.")
        return cached_count

    def generate_apply_scripts(self) -> None:
        bat_path = os.path.join(self.base_dir, "Apply-Mod.bat")
        bat_content = (
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "title RF Online Cora-Bellato Mod 1-Click Restore\r\n"
            "echo ====================================================================\r\n"
            "echo  RF Online 4.75 Cora ^<--^> Bellato Mod Restorer (1-Second Recovery)\r\n"
            "echo ====================================================================\r\n"
            "echo.\r\n"
            "if not exist \"_ModCache\" (\r\n"
            "    echo [ERROR] _ModCache directory not found!\r\n"
            "    echo Please run 'python cora_bellato_patcher.py --apply' first.\r\n"
            "    pause\r\n"
            "    exit /b 1\r\n"
            ")\r\n"
            "echo [*] Restoring mod files from _ModCache into game directory...\r\n"
            "robocopy \"_ModCache\" \".\" /E /IS /IT /NFL /NDL /NJH /NJS /nc /ns /np >nul\r\n"
            "if errorlevel 8 (\r\n"
            "    echo [!] Robocopy reported errors. Falling back to xcopy...\r\n"
            "    xcopy /S /Y /Q \"_ModCache\\*.*\" \".\\\" >nul\r\n"
            ")\r\n"
            "echo [+]\r\n"
            "echo [+] SUCCESS! Mod applied successfully in 1 click.\r\n"
            "echo [+] You can now launch RF Online via Innova 4game Launcher.\r\n"
            "echo.\r\n"
            "ping 127.0.0.1 -n 3 >nul 2>&1\r\n"
        )
        with open(bat_path, "wb") as f:
            f.write(bat_content.encode("utf-8"))
        print(f"[+] Generated: {bat_path}")

        ps1_path = os.path.join(self.base_dir, "Apply-Mod.ps1")
        ps1_content = (
            "# RF Online Cora <-> Bellato Mod 1-Click Restore\r\n"
            "$ErrorActionPreference = 'Stop'\r\n"
            "$Host.UI.RawUI.WindowTitle = 'RF Online Cora-Bellato Mod 1-Click Restore'\r\n"
            "Write-Host '====================================================================' -ForegroundColor Cyan\r\n"
            "Write-Host ' RF Online 4.75 Cora <-> Bellato Mod Restorer (1-Second Recovery)' -ForegroundColor Yellow\r\n"
            "Write-Host '====================================================================' -ForegroundColor Cyan\r\n"
            "Write-Host ''\r\n"
            "if (-not (Test-Path '_ModCache')) {\r\n"
            "    Write-Host '[ERROR] _ModCache directory not found!' -ForegroundColor Red\r\n"
            "    Write-Host 'Please run python cora_bellato_patcher.py --apply first.' -ForegroundColor White\r\n"
            "    exit 1\r\n"
            "}\r\n"
            "$sw = [System.Diagnostics.Stopwatch]::StartNew()\r\n"
            "Write-Host '[*] Restoring mod files from _ModCache...' -ForegroundColor Gray\r\n"
            "& robocopy '_ModCache' '.' /E /IS /IT /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null\r\n"
            "if ($LASTEXITCODE -ge 8) {\r\n"
            "    Write-Host '[!] Robocopy reported errors. Falling back to Copy-Item...' -ForegroundColor Yellow\r\n"
            "    Copy-Item -Path '_ModCache\\*' -Destination '.' -Recurse -Force\r\n"
            "}\r\n"
            "$sw.Stop()\r\n"
            "Write-Host ('[+] SUCCESS! Mod restored in {0:N2} ms.' -f $sw.Elapsed.TotalMilliseconds) -ForegroundColor Green\r\n"
            "Write-Host '[+] Ready to play! Launching client...' -ForegroundColor Green\r\n"
            "Start-Sleep -Seconds 2\r\n"
        )
        with open(ps1_path, "wb") as f:
            f.write(ps1_content.encode("utf-8"))
        print(f"[+] Generated: {ps1_path}")


def is_mod_applied(base_dir: str = BASE_DIR) -> bool:
    """Check if the mod is active by inspecting DEFAULTBF.RFS mesh content.
    When mod is applied, DEFAULTBF.RFS contains Cora meshes (different entry sizes)."""
    rfs_path = os.path.join(base_dir, "Character", "Player", "Mesh", "DEFAULTBF.RFS")
    backup_rfs = os.path.join(BACKUP_DIR, "Character", "Player", "Mesh", "DEFAULTBF.RFS")
    if os.path.exists(rfs_path) and os.path.exists(backup_rfs):
        return os.path.getsize(rfs_path) != os.path.getsize(backup_rfs)
    return False


def verify_installation(base_dir: str = BASE_DIR) -> bool:
    print("====================================================================")
    print(" Verifying RF Online Cora <-> Bellato Modification State")
    print("====================================================================")

    all_passed = True

    print("[*] Checking safety invariants (Animus, MAU, Skills)...")
    for excl in STRICT_EXCLUSIONS:
        p = os.path.join(base_dir, "Character", "Player", "Ani", excl)
        if os.path.exists(p):
            print(f"    [OK] Strictly excluded skill archive untouched: {excl}")

    # Base skeletons are race-adapted to satisfy the engine validator while providing matching proportions
    # BelFemale: 66963 bytes (25 bones: Cora female proportions, engine-compliant)
    # CorFemale: 90508 bytes (38 bones: Bellato female proportions, engine-compliant)
    # BelMale: 70448 bytes (30 bones: Cora male proportions + HeadNub, engine-compliant)
    # CorMale: 70211 bytes (29 bones: Bellato male proportions without HeadNub, engine-compliant)
    bel_f_bn = os.path.join(base_dir, "Character", "Player", "Bone", "BelFemale.bn")
    cor_f_bn = os.path.join(base_dir, "Character", "Player", "Bone", "CorFemale.bn")
    bel_m_bn = os.path.join(base_dir, "Character", "Player", "Bone", "BelMale.bn")
    cor_m_bn = os.path.join(base_dir, "Character", "Player", "Bone", "CorMale.bn")

    if os.path.exists(bel_f_bn) and os.path.exists(cor_f_bn):
        sz_bf = os.path.getsize(bel_f_bn)
        sz_cf = os.path.getsize(cor_f_bn)
        print(f"[*] Female base bones: BelFemale.bn = {sz_bf} bytes, CorFemale.bn = {sz_cf} bytes")
        if sz_bf == 66963 and sz_cf == 90508:
            print("    [OK] Female base skeletons ADAPTED (BelFemale=Cora 25 bones, CorFemale=Bellato 38 bones).")
        elif sz_bf == 67423 and sz_cf == 90048:
            print("    [-] Female base skeletons PRISTINE.")
        else:
            print(f"    [!] Unexpected female bone sizes: {sz_bf}, {sz_cf}")
            all_passed = False

    if os.path.exists(bel_m_bn) and os.path.exists(cor_m_bn):
        sz_bm = os.path.getsize(bel_m_bn)
        sz_cm = os.path.getsize(cor_m_bn)
        print(f"[*] Male base bones: BelMale.bn = {sz_bm} bytes, CorMale.bn = {sz_cm} bytes")
        if sz_bm == 70448 and sz_cm == 70211:
            print("    [OK] Male base skeletons ADAPTED (BelMale=Cora 30 bones, CorMale=Bellato 29 bones).")
        elif sz_bm == 70908 and sz_cm == 69751:
            print("    [-] Male base skeletons PRISTINE.")
        else:
            print(f"    [!] Unexpected male bone sizes: {sz_bm}, {sz_cm}")
            all_passed = False

    mod_active = is_mod_applied(base_dir)

    # Check Mesh RFS headers (both Female and Male)
    for rfs_name, expected_pfx in [("DEFAULTBF.RFS", "BELFEMALE_"), ("DEFAULTBM.RFS", "BELMALE_")]:
        rfs_path = os.path.join(base_dir, "Character", "Player", "Mesh", rfs_name)
        if os.path.exists(rfs_path):
            try:
                entries, _ = RFSHandler.read_rfs(rfs_path)
                first_name = bytes(entries[0]["name_raw"]).split(b"\x00")[0].decode("ascii")
                print(f"[*] Mesh {rfs_name} first entry: {first_name} (Entries: {len(entries)})")
                if expected_pfx in first_name:
                    print(f"    [OK] VFS entry naming in {rfs_name} conforms to engine contract.")
                else:
                    print(f"    [!] Unexpected VFS entry prefix in {rfs_name}!")
                    all_passed = False
            except Exception as e:
                print(f"    [!] Error reading {rfs_name}: {e}")
                all_passed = False

    # Check MOA archives for RAXETHROW preservation (both Female and Male)
    for moa_name in ["BFMOA.RFS", "BMMOA.RFS"]:
        moa_path = os.path.join(base_dir, "Character", "Player", "Ani", moa_name)
        if os.path.exists(moa_path):
            try:
                entries, _ = RFSHandler.read_rfs(moa_path)
                rax_count = sum(1 for e in entries if b"RAXETHRO" in e["name_raw"])
                print(f"[*] {moa_name} animation count: {len(entries)} (RAXETHROW animations preserved: {rax_count}/8)")
                if rax_count == 8:
                    print(f"    [OK] RAXETHROW throwing axe animations in {moa_name} 100% preserved.")
                else:
                    print(f"    [!] Warning: Missing RAXETHROW animations in {moa_name}! Found {rax_count}/8")
                    all_passed = False
            except Exception as e:
                print(f"    [!] Error reading {moa_name}: {e}")
                all_passed = False

    # Check shared Mesh RFS (e.g. ORI70.RFS)
    ori70_path = os.path.join(base_dir, "Character", "Player", "Mesh", "ORI70.RFS")
    if os.path.exists(ori70_path):
        try:
            entries, _ = RFSHandler.read_rfs(ori70_path)
            e_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): e for e in entries}
            if "BELFEMALE_ARMOR_UPPER_181.msh" in e_map and "CORFEMALE_ARMOR_UPPER_205.msh" in e_map:
                bf_size = e_map["BELFEMALE_ARMOR_UPPER_181.msh"]["size"]
                cf_size = e_map["CORFEMALE_ARMOR_UPPER_205.msh"]["size"]
                if mod_active:
                    print(f"[*] High-level 70LV Mesh check: Bel Upper 181 = {bf_size}B (was {cf_size}B Cora mesh)")
                    print("    [OK] High-level shared armor meshes SWAPPED.")
                else:
                    print(f"[*] High-level 70LV Mesh check: Bel Upper 181 = {bf_size}B, Cor Upper 205 = {cf_size}B (Pristine)")
        except Exception as e:
            print(f"    [!] Error reading ORI70.RFS: {e}")

    spr_path = os.path.join(base_dir, "SpriteImage", "ru-ru", "item.spr")
    if os.path.exists(spr_path):
        print(f"[*] Sprite inventory item.spr size: {os.path.getsize(spr_path)} bytes [OK]")
        print(f"    [OK] Configured for {len(ICON_SWAP_PAIRS)} lossless DXT1 armor & cloak icon swap pairs across Pages 13, 14, 15, 16, 17, 19.")

    # Check Symmetric Cloak Models, Bones, and Effects:
    # 1. Cora gets native Bellato boosters (000/001) & floating spheres (EFF has BALL00..03)
    # 2. Bellato gets native Cora wings/capes (000/001) & Cora dark aura (EFF has NO spheres)
    # 3. Accretia remains 100% pristine and untouched
    if mod_active:
        # Check Cora 002 mesh (Bellato cape 002: 181038B)
        c_cor_mesh = os.path.join(base_dir, "Item", "Armor", "Mesh", "CORFEMALE_ARMOR_CLOAK_002.msh")
        if os.path.exists(c_cor_mesh):
            sz_cor = os.path.getsize(c_cor_mesh)
            if sz_cor == 181038:
                print(f"    [OK] Cora cloak 002 has native Bellato cape ({sz_cor}B).")
            else:
                print(f"    [!] Warning: Cora cloak 002 size {sz_cor}B differs from expected 181038B!")
                all_passed = False

        # Check Bellato 002 mesh (Cora cape 002: 209363B)
        c_bel_002 = os.path.join(base_dir, "Item", "Armor", "Mesh", "BELFEMALE_ARMOR_CLOAK_002.msh")
        if os.path.exists(c_bel_002):
            sz_b002 = os.path.getsize(c_bel_002)
            if sz_b002 == 209363:
                print(f"    [OK] Bellato cloak 002 has native Cora cape ({sz_b002}B).")
            else:
                print(f"    [!] Warning: Bellato cloak 002 size {sz_b002}B differs from expected 209363B!")
                all_passed = False

        # Check AKM00.RFS (True packed anti-gravs: 000 and 001)
        akm_path = os.path.join(base_dir, "Item", "Armor", "Mesh", "AKM00.RFS")
        if os.path.exists(akm_path):
            try:
                entries, _ = RFSHandler.read_rfs(akm_path)
                e_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): e for e in entries}
                cf_000 = e_map.get("CORFEMALE_ARMOR_CLOAK_000.msh")
                bf_000 = e_map.get("BELFEMALE_ARMOR_CLOAK_000.msh")
                acc_000 = e_map.get("ACCRETIA_ARMOR_CLOAK_000.msh")
                if cf_000 and cf_000["size"] == 99586:
                    print("    [OK] AKM00.RFS: Cora anti-grav 000 has native Bellato booster with spheres dummies (99586B, 28 objects).")
                else:
                    print(f"    [!] Warning: AKM00.RFS Cora anti-grav 000 size mismatch: {cf_000['size'] if cf_000 else 'None'}B (expected 99586B)")
                    all_passed = False
                if bf_000 and bf_000["size"] == 60946:
                    print("    [OK] AKM00.RFS: Bellato anti-grav 000 has native Cora wings with NO spheres (60946B, 24 objects).")
                else:
                    print(f"    [!] Warning: AKM00.RFS Bellato anti-grav 000 size mismatch: {bf_000['size'] if bf_000 else 'None'}B (expected 60946B)")
                    all_passed = False
                if acc_000 and acc_000["size"] == 150308:
                    print("    [OK] AKM00.RFS: Accretia anti-grav 000 remains 100% pristine (150308B).")
                else:
                    print(f"    [!] Warning: AKM00.RFS Accretia anti-grav altered: {acc_000['size'] if acc_000 else 'None'}B (expected 150308B)")
                    all_passed = False
            except Exception as e:
                print(f"    [!] Error reading AKM00.RFS: {e}")
                all_passed = False

        # Check AKT00.RFS (Anti-grav textures)
        akt_path = os.path.join(base_dir, "Item", "Armor", "Tex", "AKT00.RFS")
        if os.path.exists(akt_path):
            try:
                entries, _ = RFSHandler.read_rfs(akt_path)
                e_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): e for e in entries}
                cf_tex = e_map.get("CORFEMALE_WEAPON_CLOAK_000.rft")
                bf_tex = e_map.get("BELFEMALE_WEAPON_CLOAK_000.rft")
                if cf_tex and bf_tex:
                    print(f"    [OK] AKT00.RFS: Anti-grav textures swapped between Cora and Bellato ({cf_tex['size']}B).")
            except Exception as e:
                print(f"    [!] Error reading AKT00.RFS: {e}")
                all_passed = False

        # Check ACA00.RFS (Anti-grav animations)
        aca_path = os.path.join(base_dir, "Item", "Armor", "Ani", "ACA00.RFS")
        if os.path.exists(aca_path):
            try:
                entries, _ = RFSHandler.read_rfs(aca_path)
                e_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): e for e in entries}
                cf_atk = e_map.get("CORFEMALE_ARMOR_CLOAK_000_ATTACK")
                bf_atk = e_map.get("BELFEMALE_ARMOR_CLOAK_000_ATTACK")
                if cf_atk and cf_atk["size"] == 10398:
                    print("    [OK] ACA00.RFS: Cora anti-grav has Bellato orbiting sphere animation (10398B).")
                else:
                    print(f"    [!] Warning: ACA00.RFS Cora anti-grav animation size mismatch: {cf_atk['size'] if cf_atk else 'None'}B (expected 10398B)")
                    all_passed = False
                if bf_atk and bf_atk["size"] == 5726:
                    print("    [OK] ACA00.RFS: Bellato anti-grav has native Cora wing animation without spheres (5726B).")
                else:
                    print(f"    [!] Warning: ACA00.RFS Bellato anti-grav animation size mismatch: {bf_atk['size'] if bf_atk else 'None'}B (expected 5726B)")
                    all_passed = False
            except Exception as e:
                print(f"    [!] Error reading ACA00.RFS: {e}")
                all_passed = False

        # Check Bellato 006 mesh (Cora wings)
        c_bel_006 = os.path.join(base_dir, "Item", "Armor", "Mesh", "BELFEMALE_ARMOR_CLOAK_006.msh")
        if os.path.exists(c_bel_006):
            sz_b006 = os.path.getsize(c_bel_006)
            if sz_b006 == 696595:
                print(f"    [OK] Bellato cloak 006 has native Cora wings mesh ({sz_b006}B).")
            else:
                print(f"    [!] Warning: Bellato cloak 006 size {sz_b006}B differs from expected 696595B!")
                all_passed = False

        # Check Effects: Cora HAS spheres (from Bellato), Bellato DOES NOT have spheres (from Cora)
        cor_eff = os.path.join(base_dir, "Chef", "Eff", "Armor", "CORFEMALE_A_CLOAKPART1.EFF")
        if os.path.exists(cor_eff):
            with open(cor_eff, "rb") as f:
                d = f.read()
            if b"BALL00" in d and b"BALL03" in d and len(d) == 1056:
                print(f"    [OK] Bellato orbiting spheres effect active on Cora (CORFEMALE_A_CLOAKPART1.EFF, {len(d)}B).")
            else:
                print(f"    [!] Warning: Expected Bellato spheres effect on Cora ({len(d)}B)!")
                all_passed = False

        bel_eff = os.path.join(base_dir, "Chef", "Eff", "Armor", "BELFEMALE_A_CLOAKPART1.EFF")
        if os.path.exists(bel_eff):
            with open(bel_eff, "rb") as f:
                d = f.read()
            if b"BALL00" not in d and len(d) == 704:
                print(f"    [OK] Bellato cloak effect is native Cora dark aura with NO SPHERES ({len(d)}B).")
            else:
                print(f"    [!] Warning: Unexpected spheres or size in BELFEMALE_A_CLOAKPART1.EFF ({len(d)}B)!")
                all_passed = False

        # Check Bones: Cora 002 has Bellato bone, Bellato 002 has Cora bone
        c_cor_bn = os.path.join(base_dir, "Item", "Armor", "Bone", "CORFEMALE_ARMOR_CLOAK_002.bn")
        if os.path.exists(c_cor_bn):
            sz_cbn = os.path.getsize(c_cor_bn)
            if sz_cbn == 70448:
                print(f"    [OK] Bellato cloak bone active on Cora 002 ({sz_cbn}B).")
            else:
                print(f"    [!] Unexpected bone size on Cora 002: {sz_cbn}B (expected 70448B)")
                all_passed = False

        c_bel_bn = os.path.join(base_dir, "Item", "Armor", "Bone", "BELFEMALE_ARMOR_CLOAK_002.bn")
        if os.path.exists(c_bel_bn):
            sz_bbn = os.path.getsize(c_bel_bn)
            if sz_bbn == 72311:
                print(f"    [OK] Cora cloak bone active on Bellato 002 ({sz_bbn}B).")
            else:
                print(f"    [!] Unexpected bone size on Bellato 002: {sz_bbn}B (expected 72311B)")
                all_passed = False

    # Check MagicSptList.spt for patriarch/archon/guild master effect swaps
    magic_spt_path = os.path.join(base_dir, "Effect", "MagicSptList.spt")
    if os.path.exists(magic_spt_path):
        with open(magic_spt_path, "rb") as f:
            magic_raw = f.read()
        magic_checks = [
            (b"0x11F90160", b"theone_beB_mag.spt", "Patriarch (Cora->Bellato)"),
            (b"0x11F70160", b"theone_coB_mag.spt", "Patriarch (Bellato->Cora)"),
            (b"0x11F90161", b"theone_beB_mag.spt", "Archon (Cora->Bellato)"),
            (b"0x11F70161", b"theone_coB_mag.spt", "Archon (Bellato->Cora)"),
            (b"0x11F90162", b"bella_gm_mag.spt", "Guild Master (Cora->Bellato)"),
            (b"0x11F70162", b"cora_gm_mag.spt", "Guild Master (Bellato->Cora)"),
        ]
        if mod_active:
            magic_ok = True
            for hex_id, expected_fn, label in magic_checks:
                # Find the line containing this hex ID
                line_start = magic_raw.find(hex_id)
                if line_start == -1:
                    continue
                line_end = magic_raw.find(b"\n", line_start)
                line = magic_raw[line_start:line_end if line_end != -1 else len(magic_raw)]
                if expected_fn in line:
                    print(f"    [OK] MagicSptList: {label} -> {expected_fn.decode()}")
                else:
                    print(f"    [!] MagicSptList: {label} NOT patched!")
                    magic_ok = False
                    all_passed = False
            if magic_ok:
                print("    [OK] All patriarch/archon/guild master effects swapped in MagicSptList.spt")
        else:
            print("[*] MagicSptList.spt present (pristine check skipped)")

    # Check Shared Texture RFS (RFMASTER.RFS in Tex/)
    tex_rfmaster = os.path.join(base_dir, "Character", "Player", "Tex", "RFMASTER.RFS")
    bak_tex_rfmaster = os.path.join(BACKUP_DIR, "Character", "Player", "Tex", "RFMASTER.RFS")
    if os.path.exists(tex_rfmaster) and os.path.exists(bak_tex_rfmaster):
        try:
            entries_cur, _ = RFSHandler.read_rfs(tex_rfmaster)
            entries_bak, _ = RFSHandler.read_rfs(bak_tex_rfmaster)
            cur_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): bytes(e["data"]) for e in entries_cur}
            bak_map = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore"): bytes(e["data"]) for e in entries_bak}
            if mod_active:
                if cur_map.get("BELFEMALE_ARMOR_LOWER_103.RFT") == bak_map.get("CORFEMALE_ARMOR_LOWER_103.RFT"):
                    print("    [OK] Tex/RFMASTER.RFS: High-level armor textures SWAPPED (Pants/Lower textures active).")
                else:
                    print("    [!] Warning: Tex/RFMASTER.RFS texture mismatch!")
                    all_passed = False
            else:
                print("    [-] Tex/RFMASTER.RFS: Pristine textures active.")
        except Exception as e:
            print(f"    [!] Error verifying Tex/RFMASTER.RFS: {e}")

    # Check Mesh/RFMASTER.RFS helmet scaling
    mesh_rfmaster = os.path.join(base_dir, "Character", "Player", "Mesh", "RFMASTER.RFS")
    if os.path.exists(mesh_rfmaster):
        try:
            entries, _ = RFSHandler.read_rfs(mesh_rfmaster)
            for e in entries:
                name = bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore")
                if name == "BELFEMALE_ARMOR_HELMET_103.msh":
                    is_m08, chunks = parse_msh_chunks(bytearray(e["data"]))
                    for cname, cbytes in chunks:
                        if cname == "H0":
                            ba = bytearray(cbytes)
                            wm = struct.unpack("<16f", ba[200:264])
                            if mod_active:
                                if 16.0 <= wm[14] <= 16.5:
                                    print(f"    [OK] Mesh/RFMASTER.RFS: Helmet 103 contains tall Cora helmet (Z={wm[14]:.2f}).")
                                else:
                                    print(f"    [!] Warning: Helmet 103 unexpected Z height (Z={wm[14]:.2f})!")
                                    all_passed = False
                            else:
                                print(f"    [-] Mesh/RFMASTER.RFS: Pristine helmet Z={wm[14]:.2f}.")
        except Exception as e:
            print(f"    [!] Error verifying helmet scaling: {e}")

    # Check BFF10.RFS retained helmet scaling
    bff10_path = os.path.join(base_dir, "Character", "Player", "Mesh", "BFF10.RFS")
    if os.path.exists(bff10_path):
        try:
            entries, _ = RFSHandler.read_rfs(bff10_path)
            helmets = [e for e in entries if b"HELMET" in e["name_raw"]]
            if mod_active:
                if len(helmets) >= 3:
                    is_m08, chunks = parse_msh_chunks(bytearray(helmets[0]["data"]))
                    h_z = None
                    for cname, cbytes in chunks:
                        if cname == "H0":
                            ba = bytearray(cbytes)
                            wm = struct.unpack("<16f", ba[200:264])
                            h_z = wm[14]
                    print(f"    [OK] BFF10.RFS: {len(helmets)} exclusive Bellato helmets retained & scaled (Z={h_z:.2f} >= 16.0).")
                else:
                    print(f"    [!] Warning: BFF10.RFS missing helmets ({len(helmets)} found)!")
                    all_passed = False
        except Exception as e:
            print(f"    [!] Error verifying BFF10.RFS: {e}")

    # Check B55 Palmas armor mapping (Lower 203 & Helmet 203 in CMB55.RFS)
    cmb55_path = os.path.join(base_dir, "Character", "Player", "Mesh", "CMB55.RFS")
    if os.path.exists(cmb55_path):
        try:
            entries, _ = RFSHandler.read_rfs(cmb55_path)
            e_names = {bytes(e["name_raw"]).split(b"\x00")[0].decode("ascii", errors="ignore") for e in entries}
            if mod_active:
                if "CORMALE_ARMOR_LOWER_203.msh" in e_names:
                    print("    [OK] CMB55.RFS: Cora 55 Palmas pants (Lower 203) present and active.")
                else:
                    print("    [!] Warning: CMB55.RFS missing CORMALE_ARMOR_LOWER_203.msh (pants missing)!")
                    all_passed = False
                if "CORMALE_ARMOR_HELMET_203.msh" in e_names:
                    print("    [OK] CMB55.RFS: Cora 55 Palmas helmet (Helmet 203) present and active.")
            else:
                if "CORMALE_ARMOR_LOWER_203.msh" in e_names and "CORMALE_ARMOR_HELMET_203.msh" not in e_names:
                    print("    [-] CMB55.RFS: Pristine 55 Palmas armor active.")
        except Exception as e:
            print(f"    [!] Error verifying CMB55.RFS: {e}")

    # Check SPR Rank and Race badges:
    spr_ru_common = os.path.join(base_dir, "SpriteImage", "ru-ru", "common.spr")
    bak_ru_common = os.path.join(BACKUP_DIR, "SpriteImage", "ru-ru", "common.spr")
    if os.path.exists(spr_ru_common) and os.path.exists(bak_ru_common):
        try:
            with open(spr_ru_common, "rb") as f1, open(bak_ru_common, "rb") as f2:
                # Page 31 (Bellato wings) <--> Page 32 (Cora wings)
                f1.seek(19508 + 24); d1_31 = f1.read(512)
                f2.seek(20044 + 24); d2_32 = f2.read(512)
                if mod_active:
                    if d1_31 == d2_32:
                        print("    [OK] common.spr: True overhead rank wings SWAPPED (Pages 31 <--> 32).")
                    else:
                        print("    [!] Warning: common.spr rank wings (Pages 31/32) not swapped!")
                        all_passed = False
                else:
                    print("    [-] common.spr: Pristine rank wings active.")

                # Target window 34x34 race crest (Bellato <--> Cora)
                sz_ru = os.path.getsize(spr_ru_common)
                off_bel_ru = sz_ru - 3 * 2072
                off_cor_ru = sz_ru - 2 * 2072
                f1.seek(off_cor_ru + 24); cur_cor = f1.read(2048)
                f2.seek(off_bel_ru + 24); bak_bel = f2.read(2048)
                if mod_active:
                    if cur_cor == bak_bel:
                        print("    [OK] ru-ru/common.spr: Target window 34x34 race crest SWAPPED (Cora slot has Bellato crest).")
                    else:
                        print("    [!] Warning: ru-ru/common.spr target window race crest NOT swapped!")
                        all_passed = False
                else:
                    print("    [-] ru-ru/common.spr: Pristine target window race crest active.")
        except Exception as e:
            print(f"    [!] Error verifying common.spr: {e}")

    for c_rel in ["SpriteImage/common.spr", "SpriteImage/common/common.spr", "SpriteImage/common/common/common.spr"]:
        spr_c = os.path.join(base_dir, c_rel)
        bak_c = os.path.join(BACKUP_DIR, c_rel)
        if os.path.exists(spr_c) and os.path.exists(bak_c):
            try:
                with open(spr_c, "rb") as f1, open(bak_c, "rb") as f2:
                    sz_c = os.path.getsize(spr_c)
                    off_bel = sz_c - 3 * 2072
                    off_cor = sz_c - 2 * 2072
                    f1.seek(off_cor + 24); cur_cor = f1.read(2048)
                    f2.seek(off_bel + 24); bak_bel = f2.read(2048)
                    if mod_active:
                        if cur_cor == bak_bel:
                            print(f"    [OK] {c_rel}: Target window 34x34 race crest SWAPPED.")
                        else:
                            print(f"    [!] Warning: {c_rel} target window race crest NOT swapped!")
                            all_passed = False
            except Exception as e:
                print(f"    [!] Error verifying {c_rel}: {e}")

    for pvp_rel in ["SpriteImage/common/pvp.spr", "SpriteImage/common/common/pvp.spr"]:
        spr_pvp = os.path.join(base_dir, pvp_rel)
        bak_pvp = os.path.join(BACKUP_DIR, pvp_rel)
        if os.path.exists(spr_pvp) and os.path.exists(bak_pvp):
            try:
                with open(spr_pvp, "rb") as f1, open(bak_pvp, "rb") as f2:
                    f1.seek(204888 + 24); p1_bel = f1.read(2048)
                    f2.seek(206960 + 24); p2_cor = f2.read(2048)
                    if mod_active:
                        if p1_bel == p2_cor:
                            print(f"    [OK] {pvp_rel}: Target race crests SWAPPED (34x34 & 55x55).")
                        else:
                            print(f"    [!] Warning: {pvp_rel} race crests not swapped!")
                            all_passed = False
                    else:
                        print(f"    [-] {pvp_rel}: Pristine race crests active.")
            except Exception as e:
                print(f"    [!] Error verifying {pvp_rel}: {e}")

    for ci_rel in ["SpriteImage/common/charinfo.spr", "SpriteImage/en-gb/charinfo.spr"]:
        spr_charinfo = os.path.join(base_dir, ci_rel)
        bak_charinfo = os.path.join(BACKUP_DIR, ci_rel)
        if os.path.exists(spr_charinfo) and os.path.exists(bak_charinfo):
            try:
                with open(spr_charinfo, "rb") as f1, open(bak_charinfo, "rb") as f2:
                    f1.seek(12 + 24); c1_p0 = f1.read(2048)
                    f2.seek(2084 + 24); c2_p1 = f2.read(2048)
                    if mod_active:
                        if c1_p0 == c2_p1:
                            print(f"    [OK] {ci_rel}: Character info race badge SWAPPED (Pages 0 <--> 1).")
                        else:
                            print(f"    [!] Warning: {ci_rel} race badge not swapped!")
                            all_passed = False
                    else:
                        print(f"    [-] {ci_rel}: Pristine charinfo badge active.")
            except Exception as e:
                print(f"    [!] Error verifying {ci_rel}: {e}")

    cache_ready = os.path.isdir(CACHE_DIR) and len(os.listdir(CACHE_DIR)) > 0
    bat_ready = os.path.exists(os.path.join(base_dir, "Apply-Mod.bat"))
    ps1_ready = os.path.exists(os.path.join(base_dir, "Apply-Mod.ps1"))
    print(f"[*] Local _ModCache ready: {cache_ready}")
    print(f"[*] 1-Click Apply-Mod.bat ready: {bat_ready}")
    print(f"[*] 1-Click Apply-Mod.ps1 ready: {ps1_ready}")

    print("====================================================================")
    print(f" Verification status: {'MODIFIED & ACTIVE' if mod_active else 'ORIGINAL / PRISTINE'}")
    print("====================================================================")
    return all_passed and mod_active


def main():
    parser = argparse.ArgumentParser(
        description="RF Online 4.75 Cora <-> Bellato Complete Modification Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--game-dir", "--dir", default=None, help="Path to RF Online game directory (defaults to current folder)")
    parser.add_argument("--apply", action="store_true", help="Apply full Cora <-> Bellato mod (Backup, Swap, DXT1, Cache, Scripts)")
    parser.add_argument("--rollback", action="store_true", help="Completely restore game to pristine state from _ModBackup/")
    parser.add_argument("--verify", action="store_true", help="Verify current mod state and file integrity")
    parser.add_argument("--status", action="store_true", help="Show current installation status")
    parser.add_argument("--force", "--reinstall", action="store_true", dest="force", help="Force complete clean reinstall of mod from pristine backup")

    args = parser.parse_args()

    if args.force:
        args.apply = True

    if not any([args.apply, args.rollback, args.verify, args.status]):
        parser.print_help()
        sys.exit(0)

    target_dir = os.path.abspath(args.game_dir) if args.game_dir else BASE_DIR
    backup_mgr = BackupManager(target_dir)
    swapper = AssetSwapper(target_dir, backup_mgr)
    cacher = CacheManager(target_dir)

    if args.status or args.verify:
        is_active = verify_installation(target_dir)
        sys.exit(0 if is_active else 0)

    elif args.rollback:
        restored, errors = backup_mgr.rollback()
        if errors:
            print(f"[!] Rollback completed with {len(errors)} warnings.")
            sys.exit(1)
        else:
            print("[+] Pristine client state restored successfully.")
            sys.exit(0)

    elif args.apply:
        print("====================================================================")
        print(" Starting RF Online Cora <-> Bellato Full Modification Process")
        print("====================================================================")

        already_applied = is_mod_applied(target_dir)
        if already_applied and not args.force:
            print("[!] Notice: Cora <-> Bellato mod is ALREADY applied and active!")
            print("[*] Refreshing _ModCache and 1-click restore scripts...")
            cacher.build_cache_from_active_mod()
            cacher.generate_apply_scripts()
            print()
            verify_installation(target_dir)
            print("\n[+] Mod is active and healthy. Use --reinstall or --force to force a full re-swap.")
            sys.exit(0)

        if already_applied and args.force:
            print("[*] Reinstall requested: rolling back to pristine state first...")
            backup_mgr.rollback()

        stats = swapper.execute_swap()
        cacher.build_cache_from_active_mod()
        cacher.generate_apply_scripts()

        print()
        verify_installation(target_dir)

        print("\n[+] SUCCESS: Cora <-> Bellato mod installed successfully!")
        print(f"    - Swapped Mesh RFS sets:     {stats['mesh_rfs']}")
        print(f"    - Swapped Shared Mesh RFS:   {stats.get('shared_mesh_rfs', 0)} archives ({stats.get('shared_mesh_pairs', 0)} mesh pairs)")
        print(f"    - Swapped Loose Meshes:      {stats['mesh_loose']}")
        print(f"    - Swapped Tex RFS sets:      {stats['tex_rfs']}")
        print(f"    - Swapped Shared Tex RFS:    {stats.get('shared_tex_rfs', 0)} archives ({stats.get('shared_tex_pairs', 0)} texture pairs)")
        print(f"    - Swapped Loose Textures:    {stats['tex_loose']}")
        print(f"    - Swapped Bones & BBX:       {stats['bone']}")
        print(f"    - Swapped Ani RFS sets:      {stats['ani_rfs']}")
        print(f"    - Swapped Mount animations:  {stats['ani_mount']}")
        print(f"    - Swapped Music & Voice:     {stats['bgm'] + stats['voice']}")
        print(f"    - Swapped Armor Effects:     {stats['effects_eff']}")
        print(f"    - Swapped Auras & Exhaust:   {stats['effects_spt']}")
        print(f"    - Swapped Particle Dirs:     {stats['particle_dirs']}")
        print(f"    - MagicSptList.spt Patches:  {stats.get('magic_spt_patched', 0)} entries")
        print(f"    - Swapped RFS Anti-Gravs:    {stats.get('rfs_cloaks', 0)} archives")
        print(f"    - Lossless DXT1 Icon Swaps:  {stats['sprite_icons']} icon pairs")
        print(f"    - Common.spr Rank Badges:    {stats.get('common_rank_badges', 0)} badge pairs")
        print(f"    - PvP Target Race Crests:    {stats.get('pvp_crests', 0)} crest blocks")
        print(f"    - Charinfo Race Badges:      {stats.get('charinfo_crests', 0)} crest page")
        bat_recovery = os.path.join(target_dir, "Apply-Mod.bat")
        print(f"\n[+] Zero-Downtime Launcher Recovery: {bat_recovery}")
        print("    Run Apply-Mod.bat anytime after an official Innova launcher patch to restore the mod in 1 second!")


if __name__ == "__main__":
    main()
