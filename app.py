import json
import os
import re

import ollama
import pandas as pd
import streamlit as st


# ---------------- PAGE SETTINGS ----------------

st.set_page_config(
    page_title="CareerAI | AI Career Planner",
    page_icon="🎯",
    layout="wide"
)

MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

try:
    OLLAMA_HOST = st.secrets["ollama"]["host"]
    TOKEN = st.secrets["ollama"].get("token", "")
except Exception:
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    TOKEN = os.getenv("OLLAMA_TOKEN", "")


# ---------------- SESSION STATE ----------------

DEFAULTS = {
    "report": None,
    "student": None,
    "student_name": "",
    "skills": "",
    "education": "",
    "study_hours": 10,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_all():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


# ---------------- DESIGN ----------------

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .hero {
        padding: 35px;
        border-radius: 18px;
        background: linear-gradient(120deg, #172554, #4338ca);
        color: white;
    }
    .hero h1 { color: white; }
    .hero p { color: #dbeafe; font-size: 17px; }
    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        min-height: 42px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- OLLAMA CLIENT ----------------

@st.cache_resource
def get_client():
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    return ollama.Client(
        host=OLLAMA_HOST,
        headers=headers,
        timeout=300,
    )


# ---------------- AI GENERATION ----------------

def generate_ai_report(student):
    prompt = f"""
You are an expert AI career mentor.

Analyze this student:

Name: {student['name']}
Skills: {student['skills']}
Target role: {student['role']}
Education: {student['education']}
Weekly study hours: {student['hours']}
Skill level: {student['level']}

Generate a realistic career development report.

RULES:
- Compare existing and required job skills.
- Identify weak and missing skills.
- Explain the importance of each skill.
- Prioritize fundamentals first.
- Generate exactly 8 weeks.
- Never exceed {student['hours']} hours in any week.
- Include topics, skills, exercises and outcomes.
- Generate exactly 3 portfolio projects.
- Do not invent qualifications or experience.
- Provide realistic preparation estimates.
- Support complete beginners.

Return ONLY valid JSON in this format:

{{
  "skill_gap": [
    {{
      "skill": "Python",
      "status": "Already Have",
      "importance": "High",
      "learning_order": 1,
      "why_it_matters": "Explanation"
    }}
  ],
  "roadmap": [
    {{
      "week": 1,
      "topics": ["Python fundamentals"],
      "skills": ["Python"],
      "exercises": ["Build a calculator"],
      "estimated_hours": 8,
      "expected_outcome": "Understand fundamentals"
    }}
  ],
  "projects": [
    {{
      "title": "Project title",
      "description": "Project description",
      "technologies": ["Python"],
      "skills_demonstrated": ["Python"],
      "difficulty": "Beginner",
      "expected_outcome": "Outcome"
    }}
  ],
  "readiness": {{
    "current_level": "Beginner",
    "important_missing_skills": ["Python"],
    "next_steps": ["Practice Python"],
    "preparation_timeline": "8 weeks",
    "career_tips": ["Build projects"]
  }}
}}

Roadmap: exactly 8 weeks.
Projects: exactly 3.
Every week's study hours must be positive and within
the student's weekly study-hour limit.
"""

    response = get_client().chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "Return valid JSON only. Be realistic.",
            },
            {"role": "user", "content": prompt},
        ],
        format="json",
        options={"temperature": 0.2},
    )

    content = response["message"]["content"].strip()
    content = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        content,
        flags=re.IGNORECASE,
    )
    return json.loads(content)


# ---------------- VALIDATION ----------------

def analyze_skill_gaps(data):
    result = data.get("skill_gap")
    if not isinstance(result, list) or not result:
        raise ValueError("Invalid skill gap analysis.")
    required = {"skill", "status", "importance", "learning_order", "why_it_matters"}
    for item in result:
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError("A skill gap item is missing required fields.")
    return result


def generate_roadmap(data, hours):
    result = data.get("roadmap")
    if not isinstance(result, list) or len(result) != 8:
        raise ValueError("AI must generate exactly 8 weeks.")

    result = sorted(result, key=lambda item: item.get("week", 0))
    required = {
        "week", "topics", "skills", "exercises",
        "estimated_hours", "expected_outcome"
    }

    for number, week in enumerate(result, 1):
        if not isinstance(week, dict) or not required.issubset(week):
            raise ValueError(f"Week {number} is missing required fields.")
        if week["week"] != number:
            raise ValueError("Invalid roadmap week numbers.")

        study = week["estimated_hours"]
        if (
            not isinstance(study, (int, float))
            or isinstance(study, bool)
            or study <= 0
            or study > hours
        ):
            raise ValueError(f"Invalid study hours in week {number}.")

        for field in ("topics", "skills", "exercises"):
            if not isinstance(week[field], list):
                raise ValueError(f"Week {number}: {field} must be a list.")

    return result


def generate_projects(data):
    result = data.get("projects")
    if not isinstance(result, list) or len(result) != 3:
        raise ValueError("AI must generate exactly 3 projects.")

    required = {
        "title", "description", "technologies",
        "skills_demonstrated", "difficulty", "expected_outcome"
    }
    for project in result:
        if not isinstance(project, dict) or not required.issubset(project):
            raise ValueError("A portfolio project is missing required fields.")
    return result


def generate_readiness_summary(data):
    result = data.get("readiness")
    required = {
        "current_level", "important_missing_skills",
        "next_steps", "preparation_timeline", "career_tips"
    }
    if not isinstance(result, dict) or not required.issubset(result):
        raise ValueError("Invalid or incomplete readiness summary.")
    return result


def create_report(student):
    with st.spinner("Gemma 4 is preparing your career roadmap..."):
        data = generate_ai_report(student)
        report = {
            "skill_gap": analyze_skill_gaps(data),
            "roadmap": generate_roadmap(data, student["hours"]),
            "projects": generate_projects(data),
            "readiness": generate_readiness_summary(data),
        }
        report["total_hours"] = sum(
            week["estimated_hours"] for week in report["roadmap"]
        )
        return report


# ---------------- DOWNLOAD REPORTS ----------------

def skill_text(student, report):
    lines = [
        "AI CAREER ROADMAP - SKILL GAP ANALYSIS",
        f"Student: {student['name']}",
        f"Target Role: {student['role']}",
        "=" * 45,
    ]

    for item in report["skill_gap"]:
        lines.extend([
            f"\nSkill: {item['skill']}",
            f"Status: {item['status']}",
            f"Importance: {item['importance']}",
            f"Learning order: {item['learning_order']}",
            f"Reason: {item['why_it_matters']}",
        ])
    return "\n".join(lines)


def roadmap_text(student, report):
    lines = [
        "PERSONALIZED 8-WEEK CAREER ROADMAP",
        f"Student: {student['name']}",
        f"Target: {student['role']}",
        f"Total hours: {report['total_hours']}",
        "=" * 45,
    ]

    for week in report["roadmap"]:
        lines.extend([
            f"\nWEEK {week['week']}",
            f"Topics: {', '.join(week['topics'])}",
            f"Skills: {', '.join(week['skills'])}",
            f"Exercises: {', '.join(week['exercises'])}",
            f"Hours: {week['estimated_hours']}",
            f"Outcome: {week['expected_outcome']}",
        ])

    lines.append("\nPORTFOLIO PROJECTS")
    for index, project in enumerate(report["projects"], 1):
        lines.extend([
            f"\n{index}. {project['title']}",
            project["description"],
            f"Technologies: {', '.join(project['technologies'])}",
            f"Difficulty: {project['difficulty']}",
            f"Expected outcome: {project['expected_outcome']}",
        ])
    return "\n".join(lines)


# ---------------- SIDEBAR ----------------

st.sidebar.title("🎯 CareerAI")
st.sidebar.caption("AI Career Guidance Platform")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Generate Roadmap",
        "Skill Gap Analysis",
        "Learning Roadmap",
        "Portfolio Projects",
        "Career Readiness",
    ],
)

st.sidebar.divider()
st.sidebar.write(f"AI Model: `{MODEL}`")


# ---------------- DASHBOARD ----------------

if page == "Dashboard":
    st.markdown(
        """
        <div class="hero">
            <h1>Build Your Future With AI 🚀</h1>
            <p>
            Analyze your skills, discover career gaps and
            create a personalized learning roadmap.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Learning Plan", "8 Weeks")
    col2.metric("Portfolio Projects", "3")
    col3.metric("AI Engine", "Gemma 4")

    st.subheader("How It Works")
    left, middle, right = st.columns(3)
    left.markdown("### 📝 Profile")
    left.write("Enter your skills and education.")
    middle.markdown("### 🧠 Analysis")
    middle.write("AI identifies your skill gaps.")
    right.markdown("### 🎯 Roadmap")
    right.write("Get a practical learning plan.")

    if st.session_state.report:
        st.success("Your latest report is saved in this session.")

    st.info("Select **Generate Roadmap** in the sidebar to begin.")


# ---------------- INPUT FORM ----------------

elif page == "Generate Roadmap":
    st.title("📝 Student Career Profile")
    st.write("Enter your details to generate your personalized career plan.")

    with st.form("career_form"):
        name = st.text_input("Student Name", key="student_name")
        skills = st.text_area(
            "Current Skills",
            key="skills",
            placeholder="Python, C, HTML, CSS, SQL",
        )
        role = st.selectbox(
            "Target Job Role",
            [
                "Python Developer",
                "AI Engineer",
                "Data Scientist",
                "Data Analyst",
                "Web Developer",
                "Machine Learning Engineer",
                "Software Developer",
            ],
        )
        education = st.text_input(
            "Current Education / Degree",
            key="education",
            placeholder="B.Tech CSE - 1st Year",
        )
        hours = st.slider(
            "Available Study Hours Per Week",
            min_value=2,
            max_value=40,
            value=10,
            key="study_hours",
        )
        level = st.selectbox(
            "Current Skill Level",
            ["Beginner", "Intermediate", "Advanced"],
        )

        submitted = st.form_submit_button(
            "🚀 Generate Career Roadmap",
            use_container_width=True,
        )

    if submitted:
        if not name.strip() or not education.strip():
            st.error("Enter your name and education.")
        else:
            student = {
                "name": name.strip(),
                "skills": skills.strip() or "No skills yet",
                "role": role,
                "education": education.strip(),
                "hours": hours,
                "level": level,
            }

            try:
                result = create_report(student)
                st.session_state.student = student
                st.session_state.report = result
                st.success("Career roadmap generated successfully!")
                st.balloons()
            except ollama.ResponseError as error:
                st.error(f"Ollama API error: {error}")
            except (ConnectionError, OSError) as error:
                st.error(f"Connection error: {error}")
            except (json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
                st.error(f"AI response validation error: {error}")
            except Exception as error:
                st.error(f"Unexpected error: {error}")

    st.button("🗑️ Clear All Inputs", on_click=clear_all)


# ---------------- LOAD SAVED REPORT ----------------

report = st.session_state.report
student = st.session_state.student


# ---------------- SKILL GAP PAGE ----------------

if page == "Skill Gap Analysis":
    st.title("📊 Skill Gap Analysis")

    if report is None:
        st.info("Generate a roadmap first.")
    else:
        df = pd.DataFrame(report["skill_gap"])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download Skill Analysis",
            data=skill_text(student, report),
            file_name="skill_gap_analysis.txt",
            mime="text/plain",
        )


# ---------------- ROADMAP PAGE ----------------

if page == "Learning Roadmap":
    st.title("📅 Your 8-Week Learning Roadmap")

    if report is None:
        st.info("Generate a roadmap first.")
    else:
        st.metric(
            "Total Estimated Study Hours",
            f"{report['total_hours']} Hours",
        )
        st.progress(0, text="Learning plan: 0 of 8 weeks completed")

        for week in report["roadmap"]:
            with st.expander(
                f"Week {week['week']} | {week['estimated_hours']} Hours"
            ):
                st.markdown("**Topics to Learn**")
                st.write(", ".join(week["topics"]))
                st.markdown("**Skills to Develop**")
                st.write(", ".join(week["skills"]))
                st.markdown("**Practical Exercises**")
                for exercise in week["exercises"]:
                    st.write(f"• {exercise}")
                st.success(week["expected_outcome"])

        st.download_button(
            "⬇️ Download Complete Roadmap",
            data=roadmap_text(student, report),
            file_name="career_roadmap.txt",
            mime="text/plain",
        )

        if st.button("🔄 Regenerate Roadmap"):
            try:
                st.session_state.report = create_report(student)
                st.success("Roadmap regenerated!")
                st.rerun()
            except Exception as error:
                st.error(f"Regeneration failed: {error}")


# ---------------- PROJECT PAGE ----------------

if page == "Portfolio Projects":
    st.title("💻 Portfolio Project Suggestions")

    if report is None:
        st.info("Generate a roadmap first.")
    else:
        for index, project in enumerate(report["projects"], 1):
            with st.container(border=True):
                st.subheader(f"{index}. {project['title']}")
                st.write(project["description"])
                st.write(f"**Difficulty:** {project['difficulty']}")
                st.write(
                    "**Technologies:** "
                    + ", ".join(project["technologies"])
                )
                st.write(
                    "**Skills:** "
                    + ", ".join(project["skills_demonstrated"])
                )
                st.success(project["expected_outcome"])


# ---------------- READINESS PAGE ----------------

if page == "Career Readiness":
    st.title("🎯 Career Readiness Summary")

    if report is None:
        st.info("Generate a roadmap first.")
    else:
        readiness = report["readiness"]
        col1, col2 = st.columns(2)
        col1.metric("Current Level", readiness["current_level"])
        col2.metric("Preparation Timeline", readiness["preparation_timeline"])

        st.subheader("Important Missing Skills")
        for skill in readiness["important_missing_skills"]:
            st.write(f"• {skill}")

        st.subheader("Recommended Next Steps")
        for step in readiness["next_steps"]:
            st.write(f"✓ {step}")

        st.subheader("Career Preparation Tips")
        for tip in readiness["career_tips"]:
            st.info(tip)

        st.caption(
            "Career preparation estimates are guidance, "
            "not a job placement guarantee."
        )
