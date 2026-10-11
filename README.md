# 건강 영상 아카이브

유튜브 건강 영상 아카이브 정적 웹사이트. GitHub Pages로 서비스됩니다.

## 구성

- `index.html` — 검색·정렬·영상 재생이 되는 단일 페이지 사이트 (외부 의존성 없음)
- `videos.json` — 영상 메타데이터 (제목, 설명, 태그, 자막 일부, 썸네일, 업로드일)
- `tools/` — 데이터 변환 스크립트
  - `csv_to_json.py` — Airtable CSV 내보내기 → videos.json
  - `airtable_to_json.py` — Airtable API fetch 결과 → videos.json

## 데이터 갱신 방법

### 자동 (권장)
주 1회 cron이 Airtable API에서 최신 데이터를 가져와 `videos.json`을 다시 만들고
이 저장소에 push합니다. 별도 조작 불필요.

### 수동
```bash
# 1) Airtable에서 가져오기 (스킬: ~/workspace/skills/airtable)
~/workspace/skills/airtable/bin/airtable_fetch.py appGwL6PPsIsZIS9a tbljINNeF0EmAMPJg \
  --view viw4626Nu6AswCSzy --out /tmp/at_all.json

# 2) 변환
python3 tools/airtable_to_json.py /tmp/at_all.json videos.json

# 3) 커밋 & push
git add videos.json && git commit -m "데이터 갱신" && git push
```

## 게시

GitHub Pages: 저장소 Settings → Pages → Deploy from branch → `main` / root.
