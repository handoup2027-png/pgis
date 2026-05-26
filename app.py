from __future__ import annotations

import html
from datetime import date
from io import BytesIO

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium


APP_TITLE = "냥이 어디냥?"
DEFAULT_CENTER = (37.5665, 126.9780)
DATA_FILE = "sample_reports.csv"

REQUIRED_COLUMNS = [
    "id",
    "목격일",
    "시간대",
    "위도",
    "경도",
    "주소/장소",
    "고양이 수",
    "연령대",
    "외형 특징",
    "TNR 여부",
    "건강 상태",
    "은신처",
    "먹이 제공처",
    "위험 요소",
    "특이사항",
]

SAMPLE_REPORTS = [
    {
        "id": 1,
        "목격일": "2026-05-03",
        "시간대": "저녁",
        "위도": 37.5669,
        "경도": 126.9787,
        "주소/장소": "시청역 인근 골목",
        "고양이 수": 3,
        "연령대": "성묘",
        "외형 특징": "고등어 무늬, 검정 턱시도",
        "TNR 여부": "중성화 확인",
        "건강 상태": "양호",
        "은신처": "상가 뒤편",
        "먹이 제공처": "급식소",
        "위험 요소": "도로 근접",
        "특이사항": "사람을 경계하지만 자주 출몰함",
    },
    {
        "id": 2,
        "목격일": "2026-05-07",
        "시간대": "야간",
        "위도": 37.5712,
        "경도": 126.9769,
        "주소/장소": "공원 산책로",
        "고양이 수": 2,
        "연령대": "새끼",
        "외형 특징": "노랑 치즈, 삼색",
        "TNR 여부": "중성화 미확인",
        "건강 상태": "양호",
        "은신처": "화단",
        "먹이 제공처": "없음",
        "위험 요소": "추위/더위 노출",
        "특이사항": "어미 고양이는 보이지 않음",
    },
    {
        "id": 3,
        "목격일": "2026-05-12",
        "시간대": "오전",
        "위도": 37.5614,
        "경도": 126.9860,
        "주소/장소": "시장 뒤편 주차장",
        "고양이 수": 5,
        "연령대": "혼합",
        "외형 특징": "검정, 치즈, 흰색 섞임",
        "TNR 여부": "모름",
        "건강 상태": "부상 의심",
        "은신처": "주차장 하부",
        "먹이 제공처": "쓰레기통",
        "위험 요소": "민원 다발, 도로 근접",
        "특이사항": "한 마리가 다리를 절뚝임",
    },
    {
        "id": 4,
        "목격일": "2026-05-17",
        "시간대": "오후",
        "위도": 37.5585,
        "경도": 126.9724,
        "주소/장소": "주택가 재개발 구역",
        "고양이 수": 4,
        "연령대": "성묘",
        "외형 특징": "검정 두 마리, 회색 한 마리",
        "TNR 여부": "중성화 미확인",
        "건강 상태": "질병 의심",
        "은신처": "폐건물",
        "먹이 제공처": "없음",
        "위험 요소": "공사장, 유기/학대 의심",
        "특이사항": "눈곱과 콧물이 보임",
    },
]


st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
)


def read_csv_bytes(raw: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(BytesIO(raw), encoding=encoding)
        except Exception as exc:  # pragma: no cover - user file dependent
            last_error = exc
    raise ValueError(f"CSV 파일을 읽을 수 없습니다: {last_error}")


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in REQUIRED_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""

    normalized = normalized[REQUIRED_COLUMNS]
    normalized["id"] = pd.to_numeric(normalized["id"], errors="coerce")
    normalized["id"] = normalized["id"].fillna(range_start(normalized)).astype(int)
    normalized["목격일"] = pd.to_datetime(normalized["목격일"], errors="coerce").dt.date
    normalized["목격일"] = normalized["목격일"].fillna(date.today())
    normalized["위도"] = pd.to_numeric(normalized["위도"], errors="coerce")
    normalized["경도"] = pd.to_numeric(normalized["경도"], errors="coerce")
    normalized["고양이 수"] = pd.to_numeric(normalized["고양이 수"], errors="coerce").fillna(1).astype(int)
    normalized = normalized.dropna(subset=["위도", "경도"])
    normalized["고양이 수"] = normalized["고양이 수"].clip(lower=1)
    return normalized.reset_index(drop=True)


def range_start(df: pd.DataFrame) -> pd.Series:
    return pd.Series(range(1, len(df) + 1), index=df.index)


@st.cache_data
def load_default_data() -> pd.DataFrame:
    try:
        return normalize_data(pd.read_csv(DATA_FILE, encoding="utf-8-sig"))
    except FileNotFoundError:
        return normalize_data(pd.DataFrame(SAMPLE_REPORTS))


def csv_download(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def marker_color(row: pd.Series) -> str:
    health = str(row["건강 상태"])
    tnr = str(row["TNR 여부"])
    risk = str(row["위험 요소"])
    if "긴급" in health or "부상" in health or "질병" in health:
        return "red"
    if "공사장" in risk or "도로" in risk or "학대" in risk:
        return "orange"
    if "확인" in tnr and "미확인" not in tnr:
        return "green"
    return "blue"


def popup_html(row: pd.Series) -> str:
    fields = [
        ("목격일", row["목격일"]),
        ("시간대", row["시간대"]),
        ("고양이 수", f"{row['고양이 수']}마리"),
        ("TNR", row["TNR 여부"]),
        ("건강", row["건강 상태"]),
        ("장소", row["주소/장소"]),
        ("위험", row["위험 요소"]),
        ("특이사항", row["특이사항"]),
    ]
    items = "".join(
        f"<b>{html.escape(label)}</b>: {html.escape(str(value))}<br>"
        for label, value in fields
        if str(value).strip()
    )
    return f"<div style='font-size: 13px; line-height: 1.5'>{items}</div>"


def build_map(df: pd.DataFrame) -> folium.Map:
    if df.empty:
        location = DEFAULT_CENTER
        zoom_start = 12
    else:
        location = (df["위도"].mean(), df["경도"].mean())
        zoom_start = 13

    map_obj = folium.Map(location=location, zoom_start=zoom_start, tiles="CartoDB dark_matter")
    cluster = MarkerCluster(name="목격 지점").add_to(map_obj)

    for _, row in df.iterrows():
        folium.Marker(
            location=(row["위도"], row["경도"]),
            popup=folium.Popup(popup_html(row), max_width=340),
            tooltip=f"{row['주소/장소']} · {row['고양이 수']}마리",
            icon=folium.Icon(color=marker_color(row), icon="info-sign"),
        ).add_to(cluster)

    if len(df) >= 2:
        heat_data = df[["위도", "경도", "고양이 수"]].values.tolist()
        HeatMap(heat_data, name="출몰 밀도", radius=22, blur=18, min_opacity=0.35).add_to(map_obj)

    folium.LayerControl(collapsed=False).add_to(map_obj)
    return map_obj


def filter_reports(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("데이터")
    uploaded = st.sidebar.file_uploader("CSV 업로드", type=["csv"])
    if uploaded is not None:
        try:
            st.session_state.reports = normalize_data(read_csv_bytes(uploaded.getvalue()))
            st.sidebar.success("CSV를 불러왔습니다.")
        except ValueError as exc:
            st.sidebar.error(str(exc))

    if st.sidebar.button("샘플 데이터로 초기화", use_container_width=True):
        st.session_state.reports = load_default_data()

    df = st.session_state.reports

    st.sidebar.download_button(
        "현재 데이터 다운로드",
        data=csv_download(df),
        file_name="nyangi_reports.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.sidebar.divider()
    st.sidebar.header("필터")
    if df.empty:
        return df

    min_date = min(df["목격일"])
    max_date = max(df["목격일"])
    date_range = st.sidebar.date_input("목격 기간", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    tnr_values = st.sidebar.multiselect("TNR 여부", sorted(df["TNR 여부"].dropna().unique()))
    health_values = st.sidebar.multiselect("건강 상태", sorted(df["건강 상태"].dropna().unique()))
    age_values = st.sidebar.multiselect("연령대", sorted(df["연령대"].dropna().unique()))

    filtered = df[(df["목격일"] >= start_date) & (df["목격일"] <= end_date)]
    if tnr_values:
        filtered = filtered[filtered["TNR 여부"].isin(tnr_values)]
    if health_values:
        filtered = filtered[filtered["건강 상태"].isin(health_values)]
    if age_values:
        filtered = filtered[filtered["연령대"].isin(age_values)]
    return filtered


def append_report() -> None:
    with st.form("new_report_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([1, 1, 1])
        sighting_date = col1.date_input("목격일", value=date.today())
        time_slot = col2.selectbox("시간대", ["새벽", "오전", "오후", "저녁", "야간"])
        cat_count = col3.number_input("고양이 수", min_value=1, max_value=50, value=1)

        col4, col5 = st.columns(2)
        latitude = col4.number_input("위도", min_value=-90.0, max_value=90.0, value=DEFAULT_CENTER[0], format="%.6f")
        longitude = col5.number_input("경도", min_value=-180.0, max_value=180.0, value=DEFAULT_CENTER[1], format="%.6f")

        place = st.text_input("주소/장소", placeholder="예: OO동 공원 북문, 시장 뒤편 주차장")

        col6, col7, col8 = st.columns(3)
        age = col6.selectbox("연령대", ["모름", "새끼", "성묘", "혼합"])
        tnr = col7.selectbox("TNR 여부", ["모름", "중성화 확인", "중성화 미확인"])
        health = col8.selectbox("건강 상태", ["양호", "부상 의심", "질병 의심", "긴급 구조 필요", "모름"])

        feature = st.text_input("외형 특징", placeholder="예: 치즈, 고등어 무늬, 귀 절개 있음")
        col9, col10 = st.columns(2)
        shelter = col9.text_input("은신처", placeholder="예: 폐건물, 화단, 주차장 하부")
        food = col10.text_input("먹이 제공처", placeholder="예: 급식소, 쓰레기통, 없음")
        risk_values = st.multiselect(
            "위험 요소",
            ["도로 근접", "공사장", "민원 다발", "추위/더위 노출", "유기/학대 의심", "없음"],
        )
        notes = st.text_area("특이사항", placeholder="관찰한 행동, 구조 필요 여부, 반복 출몰 여부 등")

        submitted = st.form_submit_button("목격 기록 추가", use_container_width=True)
        if submitted:
            current = st.session_state.reports
            next_id = int(current["id"].max()) + 1 if not current.empty else 1
            new_row = pd.DataFrame(
                [
                    {
                        "id": next_id,
                        "목격일": sighting_date,
                        "시간대": time_slot,
                        "위도": latitude,
                        "경도": longitude,
                        "주소/장소": place or "미입력",
                        "고양이 수": int(cat_count),
                        "연령대": age,
                        "외형 특징": feature,
                        "TNR 여부": tnr,
                        "건강 상태": health,
                        "은신처": shelter,
                        "먹이 제공처": food,
                        "위험 요소": ", ".join(risk_values) if risk_values else "없음",
                        "특이사항": notes,
                    }
                ]
            )
            st.session_state.reports = normalize_data(pd.concat([current, new_row], ignore_index=True))
            st.success("목격 기록을 추가했습니다.")


def metrics(df: pd.DataFrame) -> None:
    total_reports = len(df)
    total_cats = int(df["고양이 수"].sum()) if not df.empty else 0
    tnr_known = df["TNR 여부"].eq("중성화 확인").sum() if not df.empty else 0
    tnr_rate = (tnr_known / total_reports * 100) if total_reports else 0
    risk_count = df["위험 요소"].fillna("").str.contains("도로|공사장|학대|추위|더위|민원").sum() if not df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("목격 제보", f"{total_reports:,}건")
    col2.metric("관찰 개체", f"{total_cats:,}마리")
    col3.metric("TNR 확인", f"{tnr_rate:.1f}%")
    col4.metric("위험 요소", f"{risk_count:,}건")


def chart_section(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("필터 조건에 맞는 데이터가 없습니다.")
        return

    col1, col2 = st.columns(2)
    by_date = df.groupby("목격일", as_index=False)["고양이 수"].sum()
    col1.plotly_chart(
        px.line(by_date, x="목격일", y="고양이 수", markers=True, title="일자별 관찰 개체 수"),
        use_container_width=True,
    )

    by_time = df.groupby("시간대", as_index=False)["id"].count().rename(columns={"id": "제보 수"})
    order = ["새벽", "오전", "오후", "저녁", "야간"]
    by_time["시간대"] = pd.Categorical(by_time["시간대"], categories=order, ordered=True)
    by_time = by_time.sort_values("시간대")
    col2.plotly_chart(
        px.bar(by_time, x="시간대", y="제보 수", title="시간대별 제보 수"),
        use_container_width=True,
    )

    col3, col4 = st.columns(2)
    col3.plotly_chart(
        px.histogram(df, x="TNR 여부", color="TNR 여부", title="TNR 확인 현황"),
        use_container_width=True,
    )
    col4.plotly_chart(
        px.histogram(df, x="건강 상태", color="건강 상태", title="건강 상태 분포"),
        use_container_width=True,
    )


def project_summary() -> None:
    st.subheader("프로젝트 목적")
    st.write(
        "시민 제보를 바탕으로 길고양이 분포를 지도화하고, TNR 우선 지역과 급식소·보호 시설 배치에 활용할 기초 데이터를 만드는 PGIS 프로젝트입니다."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("핵심 수집 항목")
        st.markdown(
            """
            - 목격 위치, 일시, 개체 수
            - 연령대, 외형 특징, TNR 여부, 건강 상태
            - 은신처, 먹이 제공처, 도로·공사장 등 위험 요소
            - 사진과 특이사항
            """
        )
    with col2:
        st.subheader("활용 방향")
        st.markdown(
            """
            - 출몰 밀집 지역과 시간대 패턴 파악
            - 중성화 미확인 개체 우선 관리
            - 위험 지역 구조·보호 필요성 검토
            - 지자체 정책 제안과 시민 참여 홍보
            """
        )

    st.subheader("추진 단계")
    schedule = pd.DataFrame(
        [
            ["1단계", "준비", "1개월", "수집 양식 설계, 플랫폼 구축, 홍보 자료 제작"],
            ["2단계", "파일럿", "2주", "1-2개 동 테스트, 피드백 반영"],
            ["3단계", "본격 수집", "2-3개월", "대상 지역 확대, 데이터 품질 관리"],
            ["4단계", "분석", "2주", "데이터 정제, 핫스팟·밀도 분석"],
            ["5단계", "공개", "1주", "인터랙티브 지도 공개"],
            ["6단계", "정책 제안", "1주", "분석 결과 기반 지자체 제안"],
        ],
        columns=["단계", "구분", "기간", "주요 활동"],
    )
    st.dataframe(schedule, hide_index=True, use_container_width=True)


if "reports" not in st.session_state:
    st.session_state.reports = load_default_data()

st.title(APP_TITLE)
st.caption("시민 참여형 길고양이 출몰지 PGIS 지도 프로젝트")

filtered_reports = filter_reports(st.session_state.reports)
metrics(filtered_reports)

tabs = st.tabs(["지도", "목격 기록", "분석", "데이터", "기획 요약"])

with tabs[0]:
    st_folium(build_map(filtered_reports), use_container_width=True, height=620, returned_objects=[])

with tabs[1]:
    append_report()

with tabs[2]:
    chart_section(filtered_reports)

with tabs[3]:
    st.dataframe(filtered_reports.sort_values("id", ascending=False), hide_index=True, use_container_width=True)

with tabs[4]:
    project_summary()
