# 아크 더 래드 II 한국어 패치

PlayStation 게임 **아크 더 래드 II (Arc the Lad II, 1996)** 의 비공식 한국어 번역 패치입니다.

시스템 메시지, 전 스테이지 대사, 아이템·스킬·몬스터 이름, 장비·퀘스트 설명, 전투 텍스트를 한국어로 번역하고, 게임 폰트를 1,000자 이상의 한글 글리프로 교체합니다.

> **상태:** 베타. 번역 내역은 [CHANGELOG.md](CHANGELOG.md)를 참고하세요.

## 패치 적용 방법 (플레이어용)

이 저장소는 게임 데이터를 포함하지 않습니다. 본인이 직접 덤프한 원본 디스크 이미지에 패치를 적용하세요.

1. **[Releases](https://github.com/imlkh/arc-the-lad-2-korean/releases)** 에서 최신 `.xdelta` 패치와 `.cue` 파일을 내려받습니다.
2. 원본 BIN을 준비합니다. 반드시 아래 덤프여야 합니다:
   - **Arc the Lad II (Japan) (Rev 1)** — PlayStation the Best판 (SCPS-91071 / SCPS-91310)
   - 크기 `739,144,224` 바이트, MD5 `012B023097777CB6CE6A5DE5E0457022`
   - 초판(v1.0, SCPS-10026)은 이미지가 달라 지원하지 않습니다.
3. 패치를 적용합니다 — 두 방법 중 하나:
   - **웹 브라우저 (설치 불필요):** [RomPatcher.js](https://www.marcrobledo.com/RomPatcher.js/)에 원본 BIN과 `.xdelta`를 선택하고 Apply
   - **Delta Patcher (Windows/macOS/Linux):** [다운로드](https://github.com/marco-calautti/DeltaPatcher/releases) 후 원본 복사본에 적용
4. 결과 파일 이름을 `Arc the Lad II (Korean Patch).bin`으로 바꾸고, 내려받은 `.cue`와 같은 폴더에 두고 에뮬레이터에서 `.cue`를 실행합니다.

자세한 단계는 릴리스에 동봉된 `README.txt`(한국어/영어)를 참고하세요.

## 번역 범위

| 대상 | 내용 |
|------|------|
| 폰트 (`COMM.IMG`) | 한글 글리프 1,014자 교체 |
| 실행 파일 (`SCPS_100.26`) | 시스템 텍스트, 몬스터·스킬·캐릭터 이름 |
| 대사 (`S100`–`SJ00.STG`, 19개 스테이지) | 이벤트·전투 대사, 메뉴, 시스템 메시지 |
| 설명 (`SDIC` / `YGUILD` / `SMITH.BIN`) | 캐릭터·몬스터 도감, 길드 퀘스트, 장비 설명 |
| 전투 (`BEAM.DAT`) | 전투·이벤트 텍스트, 캐릭터 이름 |

## 소스에서 빌드하기 (개발자용)

**요구 사항:** Python 3 (표준 라이브러리만 사용), `xdelta3` (`brew install xdelta` / `apt install xdelta3`), 그리고 본인이 덤프한 원본 게임 파일.

```bash
# 1. 원본 디스크에서 추출한 게임 파일(COMM.IMG, *.STG, SCPS_100.26 등)을
#    이 저장소의 상위 디렉터리에 배치

# 2. 전체 패치 워크플로 실행 (폰트 + 텍스트 + 디스크 이미지)
python python/patch/patch_workflow.py --all

# 3. 배포용 xdelta 패치 패키지 생성 (검증 포함)
python python/patch/make_release_patch.py
# → output/release/<버전>/ 에 .xdelta + .cue + README.txt + SHA256SUMS.txt
```

`make_release_patch.py`는 원본 BIN의 MD5가 redump 해시와 일치하지 않으면 빌드를 거부하고, 생성한 패치를 원본에 되적용해 결과가 번역본과 바이트 단위로 일치하는지 검증한 뒤에만 패키징합니다.

### 저장소 구조

```
python/
  patch/        패치 적용 (워크플로, 폰트, VLUT, 훅, 디스크 이미지, 릴리스)
  decode/       일본어 텍스트 디코더 (STG 대사 추출)
  translation/  번역 파일 포맷 변환
  font/         한글 폰트 생성
  validation/   번역 검증 (길이, 잔여 일본어 스캔)
  tools/        커버리지 체커, 에뮬레이터 캡처 등
translated/ko/  한국어 번역 텍스트
docs/           기술 문서
```

### 기술 문서

이 프로젝트는 단순 텍스트 치환이 아니라 게임 엔진 수준의 작업을 포함합니다:

- **가변 길이 텍스트** — 일본어보다 긴 한국어 문장을 위해 MIPS 코드에 훅을 걸어 VLUT(가변 길이 룩업 테이블)로 우회: [docs/VARIABLE_LENGTH_IMPLEMENTATION.md](docs/VARIABLE_LENGTH_IMPLEMENTATION.md)
- **텍스트 인코딩** — 자체 문자 ID 체계 분석과 한글 매핑: [docs/TEXT_ENCODING.md](docs/TEXT_ENCODING.md)
- **디스크 이미지 패치** — 수정된 섹터의 EDC/ECC 체크섬 재계산: [docs/PATCHING.md](docs/PATCHING.md)
- **STG 파일 구조** — 스테이지 파일 포맷 분석: [docs/STG_STRUCTURE.md](docs/STG_STRUCTURE.md)

## 법적 고지

- 이 저장소와 릴리스에는 저작권이 있는 게임 데이터가 포함되어 있지 않습니다. 패치(`.xdelta`)에는 번역 데이터와 재계산된 체크섬만 들어 있습니다.
- 패치를 사용하려면 본인이 소유한 디스크에서 직접 덤프한 이미지가 필요합니다.
- 본 프로젝트는 무료 비공식 팬 번역이며, 소니 및 원 개발사와 무관합니다.
- Arc the Lad II © Sony Computer Entertainment / ARC Entertainment.

---

## English

Unofficial **Korean translation patch** for *Arc the Lad II* (PlayStation, 1996). Translates system text, all stage dialogue, item/skill/monster names, equipment and quest descriptions, and battle text, with a custom 1,014-glyph Korean font.

**To play:** download the `.xdelta` and `.cue` from [Releases](https://github.com/imlkh/arc-the-lad-2-korean/releases) and apply it to your own dump of **Arc the Lad II (Japan) (Rev 1)** (SCPS-91071/91310, MD5 `012B023097777CB6CE6A5DE5E0457022`) using [RomPatcher.js](https://www.marcrobledo.com/RomPatcher.js/) or [Delta Patcher](https://github.com/marco-calautti/DeltaPatcher/releases). The original v1.0 release (SCPS-10026) is a different image and is not supported.

**To build from source:** place the game files extracted from your own disc in this repo's parent directory, then run `python python/patch/patch_workflow.py --all` followed by `python python/patch/make_release_patch.py`. Requires Python 3 and `xdelta3`. The release builder refuses non-pristine source dumps and byte-verifies the patch round-trip before packaging.

Technical highlights — variable-length text via a MIPS hook and lookup tables, custom character-ID encoding, per-sector EDC/ECC recalculation — are documented in [docs/](docs/).

No copyrighted game data is distributed. This is a free, unofficial fan translation, unaffiliated with Sony or the original developers.
