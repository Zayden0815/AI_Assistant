# AI Sidebar

## Backend 실행

```powershell
cd "D:\11\backend"
python -m pip install -r requirements.txt
python api.py
```

확인:
```text
http://127.0.0.1:8000/docs
```

## Chrome Extension 로드

1. `chrome://extensions/`
2. 개발자 모드 ON
3. 압축해제된 확장 프로그램 로드
4. `extension` 폴더 선택

## FAISS DB 위치

```text
D:\ISO26262_FAISS_QWEN3
```

필요 파일:
```text
faiss.index
documents.pkl
metadata.pkl
config.json
```
