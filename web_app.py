import os

from flask import Flask, redirect, render_template, request, session, url_for

from quiz_data import QUESTIONS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

DIFFICULTIES = {"Easy": 1, "Average": 2, "Hard": 3}


def current_questions():
    difficulty = session.get("difficulty")
    return [question for question in QUESTIONS if question["difficulty"] == difficulty]


def current_game_question():
    questions = current_questions()
    index = session.get("question_index", 0)
    if 0 <= index < len(questions):
        return questions[index]
    return None


@app.get("/")
def home():
    if session.get("screen") == "game":
        question = current_game_question()
        if question is None or session.get("lives", 0) <= 0:
            session["screen"] = "summary"
    return render_template(
        "index.html",
        screen=session.get("screen", "menu"),
        name=session.get("player_name", ""),
        difficulty=session.get("difficulty", "Easy"),
        question=current_game_question() if session.get("screen") == "game" else None,
        question_number=session.get("question_index", 0) + 1,
        question_count=len(current_questions()),
        score=session.get("score", 0),
        streak=session.get("streak", 0),
        lives=session.get("lives", 0),
        attempts=session.get("attempts", 0),
        feedback=session.get("feedback"),
        feedback_kind=session.get("feedback_kind", "info"),
        rating=session.get("rating", ""),
    )


@app.post("/start")
def start_game():
    name = request.form.get("name", "").strip()[:40] or "Player"
    difficulty = request.form.get("difficulty", "Easy")
    if difficulty not in DIFFICULTIES:
        difficulty = "Easy"

    session.clear()
    session.update(
        screen="game",
        player_name=name,
        difficulty=difficulty,
        question_index=0,
        score=0,
        lives=2,
        streak=0,
        attempts=0,
        feedback=None,
        feedback_kind="info",
    )
    return redirect(url_for("home"))


@app.post("/answer")
def submit_answer():
    if session.get("screen") != "game":
        return redirect(url_for("home"))

    question = current_game_question()
    if question is None or session.get("feedback_kind") in {"correct", "failed"}:
        return redirect(url_for("home"))

    attempts = session.get("attempts", 0) + 1
    session["attempts"] = attempts
    selected = request.form.get("choice")

    if selected == question["answer"]:
        streak = session.get("streak", 0) + 1
        points = DIFFICULTIES[session["difficulty"]]
        if session["difficulty"] == "Hard" and attempts == 1:
            points += 1
        streak_bonus = streak >= 3
        if streak_bonus:
            points *= 2

        session["streak"] = streak
        session["score"] = session.get("score", 0) + points
        session["feedback_kind"] = "correct"
        session["feedback"] = (
            f"Correct! +{points} point(s)."
            + (" Streak bonus: points doubled!" if streak_bonus else "")
            + f" {question['explanation']}"
        )
    else:
        session["streak"] = 0
        if attempts < 3:
            session["feedback_kind"] = "incorrect"
            session["feedback"] = (
                f"Incorrect. Streak reset. {3 - attempts} attempt(s) remaining."
            )
        else:
            lives = session.get("lives", 0) - 1
            session["lives"] = lives
            session["feedback_kind"] = "failed"
            session["feedback"] = (
                f"Failed. Correct answer: [{question['answer']}]. "
                f"You lost 1 life. Lives left: {lives}. {question['explanation']}"
            )

    return redirect(url_for("home"))


@app.post("/next")
def next_question():
    if session.get("screen") != "game":
        return redirect(url_for("home"))
    if session.get("feedback_kind") not in {"correct", "failed"}:
        return redirect(url_for("home"))

    session["question_index"] = session.get("question_index", 0) + 1
    session["attempts"] = 0
    session["feedback"] = None
    session["feedback_kind"] = "info"

    if session["question_index"] >= len(current_questions()) or session.get("lives", 0) <= 0:
        session["screen"] = "summary"
        maximum_points = len(current_questions()) * DIFFICULTIES[session["difficulty"]]
        percentage = (session.get("score", 0) / maximum_points * 100) if maximum_points else 0
        if percentage >= 100:
            session["rating"] = "Excellent (Perfect)"
        elif percentage >= 75:
            session["rating"] = "Very Good"
        elif percentage >= 50:
            session["rating"] = "Good"
        else:
            session["rating"] = "Needs Review"

    return redirect(url_for("home"))


@app.post("/restart")
def restart_game():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
