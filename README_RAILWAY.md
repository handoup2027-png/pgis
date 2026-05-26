# 냥이 어디냥? Streamlit 배포 파일

이 폴더의 파일을 GitHub 저장소에 올린 뒤 Railway에서 해당 저장소를 연결하면 됩니다.

## 포함 파일

- `app.py`: Streamlit 앱 본문
- `requirements.txt`: Python 패키지 목록
- `railway.toml`: Railway 시작 명령 설정
- `sample_reports.csv`: 시연용 샘플 목격 데이터
- `.python-version`: Railway 빌드용 Python 3.12 지정

## Railway 배포 순서

1. 위 파일들을 한 GitHub 저장소의 루트에 올립니다.
2. Railway에서 New Project > Deploy from GitHub repo를 선택합니다.
3. 배포가 끝나면 Settings > Networking에서 Public Domain을 생성합니다.
4. 앱이 열리지 않으면 Railway 로그에서 시작 명령이 아래처럼 잡혔는지 확인합니다.

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true --browser.gatherUsageStats false
```

## 운영 전 참고

현재 앱은 CSV 업로드와 다운로드 중심의 프로토타입입니다. Railway에서 앱이 재시작되면 사용자가 화면에서 추가한 세션 데이터는 사라질 수 있으므로, 실제 시민 제보를 계속 저장하려면 Google Sheets, PostgreSQL, Supabase 같은 외부 저장소를 붙이는 것이 좋습니다.
