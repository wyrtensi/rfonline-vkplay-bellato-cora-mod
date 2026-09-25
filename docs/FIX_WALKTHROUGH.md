# Результаты: Исправление невидимых штанов (Палмас 55), значков рангов/рас и шлемов Кора <-> Беллато

## 1. Обзор проблемы и коренные причины

В ходе тестирования в игре были выявлены 3 проблемы:
1. **«штанов все еще нет» (Невидимые штаны / пустота между торсом и сапогами):**
   - У персонажа «TheEND» в сете 55 уровня Палмас (или аналог Коры) нижняя часть тела отсутствовала полностью (прозрачный разрыв).
   - **Коренная причина:** В оригинальном клиенте RF Online меши сета Палмас 55 хранятся в архивах `*B55.RFS`. Однако у Беллато и Коры используются **разные идентификаторы мешей**:
     - Беллато (`BMB55.RFS` / `BFB55.RFS`): ID **179** (Воин), **187** (Стрелок), **195** (Маг).
     - Кора (`CMB55.RFS` / `CFB55.RFS`): ID **203** (Воин), **211** (Стрелок), **219** (Маг).
     Ранее патчер выполнял простое текстовое переименование префикса `BELMALE_` $\to$ `CORMALE_`, сохраняя имя `CORMALE_ARMOR_LOWER_179.msh`. Игровой клиент Коры при надевании сета 55 уровня обращался к файлу `CORMALE_ARMOR_LOWER_203.msh`, не находил его в архиве `CMB55.RFS` и рендерил пустоту!
2. **«звания коровские у кор, ты же понимаешь что мы делаем беллато у кор?» (Иконки рангов и гербы расы):**
   - Над головой у персонажа («1st TheEND») отображались бирюзовые крылья Коры вместо розово-золотых крыльев Беллато.
   - **Коренная причина:**
     - Страницы 42–45 в `common.spr` являются монохромными цветными квадратами $29 \times 23$ пикселя. Настоящие оверхед-крылья рангов ЧВ расположены на:
       - **Страница 31** (двойные крылья Беллато, $17 \times 16$, DXT5, 512 байт) $\leftrightarrow$ **Страница 32** (двойные крылья Коры, $17 \times 16$, DXT5, 512 байт).
       - **Страница 34** (одинарное крыло Беллато, $12 \times 17$, DXT5, 512 байт) $\leftrightarrow$ **Страница 35** (одинарное крыло Коры, $12 \times 17$, DXT5, 512 байт).
     - Кроме того, клиент использует дубликат файла `SpriteImage/common/common/pvp.spr`, который не был модифицирован (патчился только `SpriteImage/common/pvp.spr`), поэтому герб в таргете оставался коровским.
3. **«шлемов все еще нет»:**
   - В сете 55 уровня Палмас у Беллато есть шлем (`179/187/195`), а у Коры в `CMB55.RFS` шлемов изначально не было. Без переназначения на `203/211/219` шлем также не мог загрузиться.
   - В общих архивах 60 (`DARKM60.RFS`) и 70 (`ORI70.RFS`, `ori6770.RFS`) шлемы Коры (207, 205) отсутствовали либо не были согласованы по текстурам.
4. **«короче последние правки ничего не изменили визуально в игре»:**
   - Процесс игры `RF_Online.exe` (PID 47704) был запущен с 09:29 и удерживал загруженные в видеопамять ресурсы. Клиент RF Online не перезагружает текстуры, спрайты и геометрию из файлов во время работы в той же локации — **для применения любых изменений диск $\to$ память требуется полный перезапуск клиента игры.**

---

## 2. Реализованные исправления в `cora_bellato_patcher.py`

### 1. Сопоставление сетов B55 (Палмас 55) с правильными ID
В `RFSHandler.swap_and_patch_rfs`:
- Для архивов `*B55.RFS` внедрено двустороннее сопоставление ID:
  - В архив Коры (`CMB55.RFS` / `CFB55.RFS`): `179` $\to$ `203`, `187` $\to$ `211`, `195` $\to$ `219`. Создаются корректные файлы `CORMALE_ARMOR_LOWER_203.msh`, `CORMALE_ARMOR_HELMET_203.msh`, `UPPER_203`, `GLOVES_203`, `SHOES_203`.
  - В архив Беллато (`BMB55.RFS` / `BFB55.RFS`): `203` $\to$ `179`, `211` $\to$ `187`, `219` $\to$ `195`.
- В текстурном архиве `CMB55.RFS` генерируются текстуры `CORMALE_ARMOR_HELMET_055WA.RFT`, `055RA.RFT`, `055FA.RFT`, а в `BMB55.RFS` сохраняются оригинальные текстуры шлемов.

### 2. Своп истинных оверхед-крыльев рангов в `common.spr`
В `SpritePatcher.swap_common_rank_badges`:
- Реализован побайтовый DXT5 обмен 512-байтных блоков:
  - **Стр. 31 $\leftrightarrow$ Стр. 32** (основные крылья 1-го ранга: Беллато розово-золотые $\leftrightarrow$ Кора бирюзовые).
  - **Стр. 34 $\leftrightarrow$ Стр. 35** (одинарные крылья).
  - Стр. 42 $\leftrightarrow$ 44 и Стр. 43 $\leftrightarrow$ 45 (вспомогательные цветные плашки).
- Патч применяется синхронно ко **всем 5 копиям** `common.spr`:
  1. `SpriteImage/ru-ru/common.spr`
  2. `SpriteImage/common.spr`
  3. `SpriteImage/common/common.spr`
  4. `SpriteImage/common/common/common.spr`
  5. `SpriteImage/en-gb/common.spr`
- Крылья Акретии (страницы 33, 36, 46, 47) остаются строго нетронутыми.

### 3. Своп гербов расы во всех копиях `pvp.spr` и `charinfo.spr`
- `SpritePatcher.swap_pvp_race_badges` теперь патчит **обе копии**:
  - `SpriteImage/common/pvp.spr`
  - `SpriteImage/common/common/pvp.spr`
  (меняются блоки $34 \times 34$ и $55 \times 55$ между Беллато и Корой, Акретия изолирована).
- `SpritePatcher.swap_charinfo_race_badges` теперь патчит:
  - `SpriteImage/common/charinfo.spr`
  - `SpriteImage/en-gb/charinfo.spr`

### 4. Инъекция шлемов в общие архивы и двусторонняя замена текстур в свободных мешах
- Внедрен метод `inject_shared_helmets`:
  - `DARKM60.RFS`: шлемы Беллато 183/191/199 дублируются как 207/215/223 для Коры, текстуры в `DARKT60.RFS` синхронизированы.
  - `ORI70.RFS` / `ori6770.RFS`: шлемы Беллато 181/189/197 дублируются как 205/213/221 для Коры.
  - `WHITEM.RFS` / `NWHITEM.RFS`: шлемы 013/014/015 синхронизированы.
- В шаге 2 `AssetSwapper.execute_swap` при обработке свободных `.msh` добавлена автозамена ссылок на текстуры (`BM_` $\leftrightarrow$ `CM_`, `BF_` $\leftrightarrow$ `CF_`, `B_M_` $\leftrightarrow$ `C_M_`, `B_F_` $\leftrightarrow$ `C_F_`, `BEMA_` $\leftrightarrow$ `COMA_`, `BEFE_` $\leftrightarrow$ `COFE_`, `Be_` $\leftrightarrow$ `Co_`).

---

## 3. Результаты верификации

Установка выполнена начисто (`python cora_bellato_patcher.py --force`).

```
====================================================================
 Verifying RF Online Cora <-> Bellato Modification State
====================================================================
[*] Checking safety invariants (Animus, MAU, Skills)...
    [OK] Strictly excluded skill archive untouched: CFETA.RFS
    [OK] Strictly excluded skill archive untouched: AC2CA.RFS
    [OK] Strictly excluded skill archive untouched: CMETA.RFS
    [OK] Strictly excluded skill archive untouched: CF2CA.RFS
    [OK] Strictly excluded skill archive untouched: CM2CA.RFS
    [OK] Strictly excluded skill archive untouched: BFETA.RFS
    [OK] Strictly excluded skill archive untouched: ACETA.RFS
    [OK] Strictly excluded skill archive untouched: BF2CA.RFS
    [OK] Strictly excluded skill archive untouched: BMETA.RFS
    [OK] Strictly excluded skill archive untouched: BM2CA.RFS
[*] Female base bones: BelFemale.bn = 66963 bytes, CorFemale.bn = 90508 bytes
    [OK] Female base skeletons ADAPTED (BelFemale=Cora 25 bones, CorFemale=Bellato 38 bones).
[*] Male base bones: BelMale.bn = 70448 bytes, CorMale.bn = 70211 bytes
    [OK] Male base skeletons ADAPTED (BelMale=Cora 30 bones, CorMale=Bellato 29 bones).
[*] Mesh DEFAULTBF.RFS first entry: BELFEMALE_DEFAULT_FACE_000.msh (Entries: 30)
    [OK] VFS entry naming in DEFAULTBF.RFS conforms to engine contract.
[*] Mesh DEFAULTBM.RFS first entry: BELMALE_DEFAULT_FACE_000.msh (Entries: 30)
    [OK] VFS entry naming in DEFAULTBM.RFS conforms to engine contract.
[*] BFMOA.RFS animation count: 200 (RAXETHROW animations preserved: 8/8)
    [OK] RAXETHROW throwing axe animations in BFMOA.RFS 100% preserved.
[*] BMMOA.RFS animation count: 200 (RAXETHROW animations preserved: 8/8)
    [OK] RAXETHROW throwing axe animations in BMMOA.RFS 100% preserved.
[*] High-level 70LV Mesh check: Bel Upper 181 = 484310B (was 294317B Cora mesh)
    [OK] High-level shared armor meshes SWAPPED.
[*] Sprite inventory item.spr size: 33862604 bytes [OK]
    [OK] Configured for 560 lossless DXT1 armor & cloak icon swap pairs across Pages 13, 14, 15, 16, 17, 19.
    [OK] Cora cloak 002 has native Bellato cape (181038B).
    [OK] Bellato cloak 002 has native Cora cape (209363B).
    [OK] AKM00.RFS: Cora anti-grav 000 has native Bellato booster with spheres dummies (99586B, 28 objects).
    [OK] AKM00.RFS: Bellato anti-grav 000 has native Cora wings with NO spheres (60946B, 24 objects).
    [OK] AKM00.RFS: Accretia anti-grav 000 remains 100% pristine (150308B).
    [OK] AKT00.RFS: Anti-grav textures swapped between Cora and Bellato (5592560B).
    [OK] ACA00.RFS: Cora anti-grav has Bellato orbiting sphere animation (10398B).
    [OK] ACA00.RFS: Bellato anti-grav has native Cora wing animation without spheres (5726B).
    [OK] Bellato cloak 006 has native Cora wings mesh (696595B).
    [OK] Bellato orbiting spheres effect active on Cora (CORFEMALE_A_CLOAKPART1.EFF, 1056B).
    [OK] Bellato cloak effect is native Cora dark aura with NO SPHERES (704B).
    [OK] Bellato cloak bone active on Cora 002 (70448B).
    [OK] Cora cloak bone active on Bellato 002 (72311B).
    [OK] MagicSptList: Patriarch (Cora->Bellato) -> theone_beB_mag.spt
    [OK] MagicSptList: Patriarch (Bellato->Cora) -> theone_coB_mag.spt
    [OK] MagicSptList: Archon (Cora->Bellato) -> theone_beB_mag.spt
    [OK] MagicSptList: Archon (Bellato->Cora) -> theone_coB_mag.spt
    [OK] MagicSptList: Guild Master (Cora->Bellato) -> bella_gm_mag.spt
    [OK] MagicSptList: Guild Master (Bellato->Cora) -> cora_gm_mag.spt
    [OK] All patriarch/archon/guild master effects swapped in MagicSptList.spt
    [OK] Tex/RFMASTER.RFS: High-level armor textures SWAPPED (Pants/Lower textures active).
    [OK] Mesh/RFMASTER.RFS: Helmet 103 contains tall Cora helmet (Z=16.29).
    [OK] BFF10.RFS: 3 exclusive Bellato helmets retained & scaled (Z=16.31 >= 16.0).
    [OK] CMB55.RFS: Cora 55 Palmas pants (Lower 203) present and active.
    [OK] CMB55.RFS: Cora 55 Palmas helmet (Helmet 203) present and active.
    [OK] common.spr: True overhead rank wings SWAPPED (Pages 31 <--> 32).
    [OK] ru-ru/common.spr: Target window 34x34 race crest SWAPPED (Cora slot has Bellato crest).
    [OK] SpriteImage/common/pvp.spr: Target race crests SWAPPED (34x34 & 55x55).
    [OK] SpriteImage/common/common/pvp.spr: Target race crests SWAPPED (34x34 & 55x55).
    [OK] SpriteImage/common/charinfo.spr: Character info race badge SWAPPED (Pages 0 <--> 1).
    [OK] SpriteImage/en-gb/charinfo.spr: Character info race badge SWAPPED (Pages 0 <--> 1).
[*] Local _ModCache ready: True (5125 files)
[*] 1-Click Apply-Mod.bat ready: True
[*] 1-Click Apply-Mod.ps1 ready: True
====================================================================
 Verification status: MODIFIED & ACTIVE
====================================================================
```

---

## 4. Дополнительное исправление: Значок расы («ранг») в рамке таргета

Пользователь предоставил скриншот окна таргета (персонаж «DON»), где рядом с ником всё ещё отображался бирюзовый герб Коры.

### Причина:
- В клиенте RF Online значок расы в рамке таргета читается из файла **`common.spr`**:
  - `common.spr` содержит блок из четырёх спрайтов $34 \times 34$ DXT1 в самом конце файла:
    - Смещение `file_size - 3 * 2072`: значок **Беллато** (золотой/розовый цветок/птица).
    - Смещение `file_size - 2 * 2072`: значок **Коры** (бирюзовый серп/змей).
    - Смещение `file_size - 1 * 2072`: значок **Акретии** (не трогается).
  - В клиенте существует 4 копии файла: `ru-ru/common.spr`, `SpriteImage/common.spr`, `SpriteImage/common/common.spr`, `SpriteImage/common/common/common.spr`.
  - Клиент загружает значки из основного `SpriteImage/common.spr` (Common), который до этого момента не был модифицирован.

### Решение:
1. В `SpritePatcher.swap_common_rank_badges()` исправлена ошибка и выполнен побайтовый своп во **всех 4 копиях** `common.spr`:
   - `SpriteImage/ru-ru/common.spr`
   - `SpriteImage/common.spr`
   - `SpriteImage/common/common.spr`
   - `SpriteImage/common/common/common.spr`
2. В `verify_installation()` добавлены тесты целостности для всех копий `common.spr` (все проверки успешно пройдены `[OK]`).
3. Локальный кэш `_ModCache/` и файл быстрого наката `Apply-Mod.bat` полностью обновлены новыми файлами.

---

## 5. Инструкция для игрока

> [!IMPORTANT]
> **Перезапуск клиента игры обязателен!**
> Клиент `RF_Online.exe` загружает 3D-модели, текстуры и спрайты интерфейса в память/видеопамять один раз при запуске игры. Изменения, внесённые на диск, не обновляются на лету в уже запущенном процессе.
> 
> Чтобы увидеть новые гербы в таргете, штаны и шлемы:
> 1. Полностью закройте клиент RF Online (`RF_Online.exe`).
> 2. Запустите игру снова (через лаунчер Фогейм / 4game).
> 3. Если лаунчер восстановит файлы во время проверки — запустите `Apply-Mod.bat` (он мгновенно накатит мод из `_ModCache/`).
