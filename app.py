import streamlit as st
import openai
import time

# === 기본 설정 및 세션 상태 초기화 ===
st.set_page_config(page_title="조선/웹툰 대본 장인 4.0 (떡상기조+나레이션)", layout="wide")

# 세션 상태 변수 (새로고침 해도 데이터 유지)
if 'analyzed_structure' not in st.session_state: st.session_state['analyzed_structure'] = None
if 'topic_ideas' not in st.session_state: st.session_state['topic_ideas'] = [] 
if 'outline_list' not in st.session_state: st.session_state['outline_list'] = []
if 'generated_chapters' not in st.session_state: st.session_state['generated_chapters'] = []
if 'current_chapter_index' not in st.session_state: st.session_state['current_chapter_index'] = 0
if 'story_context_summary' not in st.session_state: st.session_state['story_context_summary'] = "이야기 시작 전."

# === UI 헤더 ===
st.title("📜 조선/웹툰 대본 장인 4.0 (기조 유지 & 나레이션 강화)")
st.markdown("---")

# === 사이드바 설정 ===
with st.sidebar:
    st.header("⚙️ 설정")
    st.info("💡 **OpenAI API 키가 필요합니다.**\n\n1. https://platform.openai.com/account/api-keys 에서 API 키 발급\n2. 아래에 입력하세요")
    api_key = st.text_input("OpenAI API 키 입력 (sk-로 시작)", type="password", placeholder="sk-...")
    
    st.markdown("### 🎨 스타일")
    style_option = st.radio("스타일 선택", ("조선 웹툰 (사극톤)", "2D 웹툰 (현대/트렌디)"))
    
    st.markdown("### ⏱️ 길이")
    length_option = st.radio("목표 길이 선택", ("1분 (쇼츠 - 단편)", "30분 (중편 - 챕터 생성)", "1시간 (장편 - 챕터 생성)"))
    
    is_long_form = length_option != "1분 (쇼츠 - 단편)"
    
    # 스타일별 프롬프트 정의
    def get_style_prompts(style_opt, length_opt):
        if style_opt == "조선 웹툰 (사극톤)":
            tone = "조선시대 야담(Yadam) 스타일. 구수하고 맛깔나는 옛날 이야기 어조. '하오체'와 '해라체'를 적절히 섞은 나레이션."
            img_style = "Joseon dynasty webtoon style, ink wash painting texture, dramatic lighting, traditional Korean attire (Hanbok)."
        else:
            tone = "현대적인 웹툰/드라마 리뷰 스타일. 빠르고 트렌디한 어조. 인터넷 밈을 적절히 섞은 나레이션."
            img_style = "Modern 2D webtoon style, vibrant colors, sharp lines, trendy fashion, dynamic angles, digital comic book art."
        
        length_guide = "핵심만 임팩트 있게 (약 500자)" if length_opt == "1분 (쇼츠 - 단편)" else "상황 묘사 나레이션 위주로 풍부하게 (챕터당 2000자 이상)"
        return tone, length_guide, img_style

    tone_prompt, length_guide_prompt, img_style_prompt = get_style_prompts(style_option, length_option)

    client = None
    if api_key:
        if not api_key.startswith('sk-'):
            st.error("⚠️ OpenAI API 키는 'sk-'로 시작해야 합니다.")
        else:
            client = openai.OpenAI(api_key=api_key)
            st.success("✅ API 키 연결 완료")
    else:
        st.warning("⚠️ API 키를 입력해주세요.")

# === 1. 벤치마킹 단계 ===
with st.expander("1️⃣ [단계 1] 떡상 대본 구조 벤치마킹 (클릭하여 열기/닫기)", expanded=True if not st.session_state['analyzed_structure'] else False):
    col1, col2 = st.columns(2)
    with col1:
        ref_script = st.text_area("참고할 대본 입력", height=150, placeholder="벤치마킹하고 싶은 대본을 붙여넣으세요.")
    with col2:
        if st.button("구조 분석 실행"):
            if not api_key or not ref_script:
                st.error("API 키와 대본을 확인해주세요.")
            else:
                try:
                    with st.spinner("구조를 분석하는 중이오..."):
                        # ★분석 프롬프트 강화: 기조 파악 집중
                        analysis_prompt = f"다음 대본을 분석하여, 시청자를 붙잡아두는 '떡상 요인'(Hook, 갈등 고조, 반전, 카타르시스 등)이 담긴 핵심 구조를 5단계로 명확히 추출하라.\n\n[대본]\n{ref_script}"
                        response = client.chat.completions.create(
                            model="gpt-4o", messages=[{"role": "system", "content": "당신은 유튜브 대본 분석 전문가입니다."}, {"role": "user", "content": analysis_prompt}]
                        )
                        st.session_state['analyzed_structure'] = response.choices[0].message.content
                    st.success("분석 완료! (이 기조는 모든 챕터 생성에 반영됩니다)")
                except Exception as e:
                    st.error(f"에러가 발생했습니다: {e}")

        if st.session_state['analyzed_structure']:
            st.info(st.session_state['analyzed_structure'])

st.markdown("---")

# === 2. 주제 선정 단계 ===
st.subheader("2️⃣ [단계 2] 주제 선정 및 기획")
col_idea1, col_idea2 = st.columns([1, 2])

with col_idea1:
    if st.button("✨ AI 주제 추천받기"):
        if not api_key or not st.session_state['analyzed_structure']:
            st.error("API 키와 구조 분석이 필요합니다.")
        else:
            try:
                with st.spinner("주제 생각 중..."):
                    idea_prompt = f"""
                    [분석된 떡상 구조] {st.session_state['analyzed_structure']}
                    [타겟 스타일] {style_option}
                    위 성공 구조를 가장 잘 살릴 수 있는 조회수 높은 야담/웹툰 영상 주제(제목+로그라인) 5가지를 추천해줘.
                    """
                    response = client.chat.completions.create(
                        model="gpt-4o", messages=[{"role": "user", "content": idea_prompt}]
                    )
                    raw_ideas = response.choices[0].message.content.split('\n')
                    st.session_state['topic_ideas'] = [idea for idea in raw_ideas if idea.strip()]
            except Exception as e:
                st.error(f"추천 중 에러 발생: {e}")

with col_idea2:
    selected_idea = ""
    if st.session_state['topic_ideas']:
        selected_idea = st.radio("추천 주제 목록", st.session_state['topic_ideas'])

final_topic = st.text_input("최종 결정된 주제", value=selected_idea)

st.markdown("---")
st.subheader("3️⃣ [단계 3] 대본 생성 시작")

# --- 쇼츠 처리 ---
if not is_long_form:
    if st.button("쇼츠 대본 생성 시작"):
        if not final_topic: st.error("주제를 입력해주세요.")
        else:
            try:
                short_prompt = f"""
                [분석된 떡상 구조(기조)] {st.session_state['analyzed_structure']}
                [주제] {final_topic}
                [스타일] {tone_prompt}
                [요청] 위 구조를 완벽히 반영하여 1분 쇼츠 대본 작성.
                **나레이션(NA) 비중 80% 이상.** 성우가 읽었을 때 몰입감 있는 문체 사용.
                마지막에 이미지 프롬프트 포함.
                """
                with st.spinner("작성 중..."):
                    stream = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": short_prompt}], stream=True)
                    st.write_stream(stream)
            except Exception as e:
                st.error(f"에러 발생: {e}")

# --- 장편 처리 ---
else:
    # A. 목차 생성
    if st.button("Step A. 목차(아웃라인) 생성하기"):
        if not final_topic: st.error("주제를 입력해주세요.")
        else:
            try:
                target_chapters = 6 if length_option == "30분 (중편 - 챕터 생성)" else 10
                outline_prompt = f"""
                [분석된 떡상 구조] {st.session_state['analyzed_structure']}
                [주제] {final_topic}
                [목표] 위 떡상 구조의 흐름을 완벽하게 따르는 {target_chapters}개의 챕터 목차 작성.
                """
                with st.spinner("목차 생성 중..."):
                    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": outline_prompt}])
                    st.session_state['outline_list'] = [line for line in response.choices[0].message.content.split('\n') if line.strip()]
                    st.session_state['generated_chapters'] = []
                    st.session_state['current_chapter_index'] = 0
                    st.session_state['story_context_summary'] = "이야기 시작 전."
                    st.rerun()
            except Exception as e:
                st.error(f"목차 생성 중 에러: {e}")

    # B. 챕터별 생성
    if st.session_state['outline_list']:
        st.markdown(f"### 📋 진행 상황 ({st.session_state['current_chapter_index']}/{len(st.session_state['outline_list'])})")
        
        current_idx = st.session_state['current_chapter_index']
        total_chapters = len(st.session_state['outline_list'])
        st.progress(current_idx / total_chapters if total_chapters > 0 else 0)

        if current_idx < total_chapters:
            current_chapter_name = st.session_state['outline_list'][current_idx]
            st.write(f"👉 **현재 작업할 챕터: {current_chapter_name}**")
            
            if st.button(f"Step B. '{current_chapter_name}' 생성 시작"):
                try:
                    with st.spinner(f"'{current_chapter_name}' 작성 중... (기조 반영 & 나레이션 쓰는 중)"):
                        # ★★★ 핵심: 매 챕터마다 '분석된 구조'를 주입하여 기조 유지 ★★★
                        chapter_prompt = f"""
                        당신은 야담(이야기) 유튜버의 메인 작가입니다.
                        총 {total_chapters}개의 챕터 중 {current_idx + 1}번째 챕터: "{current_chapter_name}"를 작성하세요.
                        
                        [주제] {final_topic}
                        [스타일] {tone_prompt}
                        
                        [★지켜야 할 떡상 기조(분석된 구조)]
                        {st.session_state['analyzed_structure']}
                        -> 지시: 위 구조의 호흡과 시청자 후킹 요소를 이번 챕터 작성 시에도 반드시 유지하십시오.
                        
                        [이전 줄거리] {st.session_state['story_context_summary']}
                        
                        [★작성 규칙 - 나레이션 강화]
                        1. **나레이션(NA) 중심:** (NA) 지문을 사용하여 상황, 배경, 인물의 미세한 심리를 아주 상세하고 맛깔나게 묘사하십시오. (전체 분량의 70% 이상)
                        2. **대사:** 인물 간의 대사는 긴장감을 주는 용도로 짧고 굵게 사용하십시오.
                        3. **묘사 예시:** "슬펐다" (X) -> "(NA) 가슴 한구석이 썩은 동아줄 끊어지듯 툭 하고 내려앉는 것 아니겠소?" (O)
                        
                        [마무리]
                        대본 끝에 '---IMAGE_PROMPT---'를 넣고, 썸네일용 AI 이미지 프롬프트(영어) 3개를 작성하세요.
                        """
                        
                        response = client.chat.completions.create(
                            model="gpt-4o", messages=[{"role": "user", "content": chapter_prompt}], temperature=0.7
                        )
                        full_response = response.choices[0].message.content
                        
                        parts = full_response.split('---IMAGE_PROMPT---')
                        script_part = parts[0].strip()
                        image_prompt_part = parts[1].strip() if len(parts) > 1 else "이미지 프롬프트 생성 실패"

                        st.session_state['generated_chapters'].append({
                            "title": current_chapter_name, "script": script_part, "image_prompts": image_prompt_part
                        })

                        summary_res = client.chat.completions.create(
                            model="gpt-3.5-turbo", 
                            messages=[{"role": "user", "content": f"다음 챕터 연결을 위해 내용을 3줄 요약: {script_part}"}]
                        )
                        st.session_state['story_context_summary'] = summary_res.choices[0].message.content
                        
                        st.session_state['current_chapter_index'] += 1
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"⚠️ 에러가 발생했습니다: {e}")
                    st.error("잠시 후 다시 버튼을 눌러주세요.")

        else:
            st.success("🎉 모든 챕터 작성 완료!")

# === 4. 결과 확인 및 다운로드 ===
if st.session_state['generated_chapters']:
    st.markdown("---")
    st.subheader("4️⃣ 결과물 및 다운로드")
    
    # 전체 대본 합치기
    full_script = f"제목: {final_topic}\n\n"
    for chapter in st.session_state['generated_chapters']:
        full_script += f"### {chapter['title']}\n{chapter['script']}\n\n"
    
    # ★ 다운로드 버튼 ★
    st.download_button(
        label="📥 전체 대본 텍스트 파일(.txt) 다운로드",
        data=full_script,
        file_name=f"{final_topic}_대본.txt",
        mime="text/plain"
    )

    tab1, tab2 = st.tabs(["📜 전체 대본 미리보기", "🖼️ 이미지 프롬프트"])
    with tab1:
        st.text_area("대본 내용", full_script, height=500)
    with tab2:
        for c in st.session_state['generated_chapters']:
            st.code(f"[{c['title']}]\n{c['image_prompts']}")
