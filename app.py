import os
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session, redirect, url_for, flash, Response

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "lucky_wheel.db"))).resolve()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(16))

FORTUNES = [
    {"title": "오늘은 흐름이 좋은 날", "msg": "작은 인사와 빠른 응답이 생각보다 큰 호감을 만듭니다. 오늘은 먼저 움직이는 사람이 유리합니다.", "lucky": "행운 포인트: 오전 10시 전 결단"},
    {"title": "집중력이 살아나는 날", "msg": "한 번에 많은 일을 벌이기보다, 가장 중요한 한 가지를 먼저 끝내면 전체 리듬이 좋아집니다.", "lucky": "행운 포인트: 가장 어려운 일부터"},
    {"title": "좋은 소식이 스쳐가는 날", "msg": "사소한 대화나 우연한 만남에서 힌트를 얻을 수 있습니다. 평소보다 주변 말을 한 번 더 들어보세요.", "lucky": "행운 포인트: 복도에서의 짧은 대화"},
    {"title": "꾸준함이 빛나는 날", "msg": "눈에 띄는 성과보다 안정적인 실행이 더 높은 평가로 이어질 수 있습니다. 오늘은 기본기가 무기입니다.", "lucky": "행운 포인트: 체크리스트 점검"},
    {"title": "타이밍 감각이 중요한 날", "msg": "무리하게 밀어붙이기보다 한 박자 보고 들어가면 성과가 커집니다. 속도보다 타이밍입니다.", "lucky": "행운 포인트: 점심 이후 제안"},
    {"title": "협업운이 좋은 날", "msg": "혼자 해결하려 하지 말고 필요한 도움을 명확하게 요청해 보세요. 연결이 성과를 만듭니다.", "lucky": "행운 포인트: 먼저 질문하기"},
    {"title": "작은 용기가 보상을 부르는 날", "msg": "평소 망설이던 의견도 오늘은 간결하게 말하면 통할 가능성이 높습니다.", "lucky": "행운 포인트: 짧고 명확한 한마디"},
    {"title": "차분함이 승부를 가르는 날", "msg": "예상 밖 변수가 생겨도 침착함을 유지하면 오히려 신뢰를 얻습니다. 반응보다 판단이 중요합니다.", "lucky": "행운 포인트: 서두르지 않기"},
    {"title": "정리정돈이 운을 여는 날", "msg": "메일함, 메모, 책상 위를 가볍게 정리하면 머리도 함께 맑아집니다. 의외의 효율이 생깁니다.", "lucky": "행운 포인트: 오전 5분 정리"},
    {"title": "기분 좋은 반전이 있는 날", "msg": "크게 기대하지 않은 일에서 만족스러운 결과가 생길 수 있습니다. 가벼운 마음이 오히려 강점입니다.", "lucky": "행운 포인트: 부담 없이 시작하기"},
]

VOUCHER_MESSAGES = [
    "축하합니다. 오늘의 5,000원 상품권에 당첨되었습니다. 기분 좋게 하루를 시작해 보세요.",
    "좋은 기운이 도착했습니다. 5,000원 상품권 당첨입니다!",
    "오늘의 출근 운이 강하네요. 5,000원 상품권을 받았습니다."
]

COFFEE_MESSAGES = [
    "와, 커피 기프티콘 당첨입니다. 오늘 한 잔의 여유를 즐겨보세요.",
    "커피 한 잔이 따라오는 날입니다. 기프티콘 당첨!",
    "출근 텐션 상승! 커피 기프티콘이 준비되었습니다."
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            spin_date TEXT NOT NULL,
            result_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            claim_code TEXT,
            power INTEGER NOT NULL DEFAULT 0,
            redeemed INTEGER NOT NULL DEFAULT 0,
            played_at TEXT NOT NULL,
            UNIQUE(employee_id, spin_date)
        )
    """)
    conn.commit()
    conn.close()


def today_key():
    return datetime.now().strftime("%Y-%m-%d")


def today_display():
    return datetime.now().strftime("%Y.%m.%d")


def normalize_employee_id(value: str) -> str:
    return (value or "").strip()


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)
    return wrapped


def choose_result():
    roll = secrets.randbelow(10000) / 100
    if roll < 90:
        kind = "fortune"
    elif roll < 97:
        kind = "voucher"
    else:
        kind = "coffee"

    if kind == "fortune":
        idx = secrets.randbelow(len(FORTUNES))
        fortune = FORTUNES[idx]
        return {
            "result_type": "fortune",
            "title": fortune["title"],
            "message": f'{fortune["msg"]} {fortune["lucky"]}',
            "claim_code": None,
        }

    claim_suffix = secrets.token_hex(3).upper()
    if kind == "voucher":
        idx = secrets.randbelow(len(VOUCHER_MESSAGES))
        return {
            "result_type": "voucher",
            "title": "축하합니다!",
            "message": VOUCHER_MESSAGES[idx],
            "claim_code": f"GV-{datetime.now().strftime('%Y%m%d')}-{claim_suffix}",
        }

    idx = secrets.randbelow(len(COFFEE_MESSAGES))
    return {
        "result_type": "coffee",
        "title": "와, 당첨입니다!",
        "message": COFFEE_MESSAGES[idx],
        "claim_code": f"CF-{datetime.now().strftime('%Y%m%d')}-{claim_suffix}",
    }


def get_existing_spin(employee_id: str):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM spins WHERE employee_id = ? AND spin_date = ?",
        (employee_id, today_key())
    ).fetchone()
    conn.close()
    return row


def spin_to_dict(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "employee_id": row["employee_id"],
        "spin_date": row["spin_date"],
        "result_type": row["result_type"],
        "title": row["title"],
        "message": row["message"],
        "claim_code": row["claim_code"],
        "power": row["power"],
        "redeemed": bool(row["redeemed"]),
        "played_at": row["played_at"],
    }


@app.route("/")
def index():
    return render_template("index.html", today=today_display())


@app.get("/api/check")
def api_check():
    employee_id = normalize_employee_id(request.args.get("employee_id"))
    if not employee_id:
        return jsonify({"ok": False, "message": "사번이 필요합니다."}), 400

    row = get_existing_spin(employee_id)
    if row:
        return jsonify({
            "ok": True,
            "already_played": True,
            "result": spin_to_dict(row),
            "message": f"이미 오늘 참여했습니다. ({today_display()}) 같은 사번으로는 하루 1회만 가능합니다."
        })
    return jsonify({
        "ok": True,
        "already_played": False,
        "message": f"참여 가능. {employee_id} 사번은 오늘 아직 참여하지 않았습니다."
    })


@app.post("/api/spin")
def api_spin():
    data = request.get_json(silent=True) or {}
    employee_id = normalize_employee_id(data.get("employee_id"))
    power = int(max(0, min(100, int(data.get("power", 0) or 0))))

    if not employee_id:
        return jsonify({"ok": False, "message": "사번을 먼저 입력해 주세요."}), 400
    if power < 12:
        return jsonify({"ok": False, "message": "조금 더 세게 당겨주세요."}), 400

    existing = get_existing_spin(employee_id)
    if existing:
        return jsonify({
            "ok": True,
            "already_played": True,
            "result": spin_to_dict(existing),
            "message": f"이미 오늘 참여했습니다. ({today_display()}) 같은 사번으로는 하루 1회만 가능합니다."
        })

    result = choose_result()
    played_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO spins (employee_id, spin_date, result_type, title, message, claim_code, power, played_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            employee_id,
            today_key(),
            result["result_type"],
            result["title"],
            result["message"],
            result["claim_code"],
            power,
            played_at
        ))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM spins WHERE employee_id = ? AND spin_date = ?",
            (employee_id, today_key())
        ).fetchone()
    except sqlite3.IntegrityError:
        row = conn.execute(
            "SELECT * FROM spins WHERE employee_id = ? AND spin_date = ?",
            (employee_id, today_key())
        ).fetchone()
        conn.close()
        return jsonify({
            "ok": True,
            "already_played": True,
            "result": spin_to_dict(row),
            "message": f"이미 오늘 참여했습니다. ({today_display()}) 같은 사번으로는 하루 1회만 가능합니다."
        })
    conn.close()

    return jsonify({
        "ok": True,
        "already_played": False,
        "result": spin_to_dict(row),
        "message": f"참여 완료. {today_display()} 기준 오늘의 결과가 저장되었습니다."
    })


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    password = os.getenv("ADMIN_PASSWORD", "change-me")
    if request.method == "POST":
        if request.form.get("password", "") == password:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("비밀번호가 올바르지 않습니다.")
    return render_template("admin_login.html")


@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()

    stats = {
        "today_total": conn.execute(
            "SELECT COUNT(*) AS c FROM spins WHERE spin_date = ?", (today_key(),)
        ).fetchone()["c"],
        "today_voucher": conn.execute(
            "SELECT COUNT(*) AS c FROM spins WHERE spin_date = ? AND result_type = 'voucher'", (today_key(),)
        ).fetchone()["c"],
        "today_coffee": conn.execute(
            "SELECT COUNT(*) AS c FROM spins WHERE spin_date = ? AND result_type = 'coffee'", (today_key(),)
        ).fetchone()["c"],
        "today_fortune": conn.execute(
            "SELECT COUNT(*) AS c FROM spins WHERE spin_date = ? AND result_type = 'fortune'", (today_key(),)
        ).fetchone()["c"],
        "all_total": conn.execute("SELECT COUNT(*) AS c FROM spins").fetchone()["c"],
        "pending_claims": conn.execute(
            "SELECT COUNT(*) AS c FROM spins WHERE claim_code IS NOT NULL AND redeemed = 0"
        ).fetchone()["c"],
    }

    recent_rows = conn.execute("""
        SELECT * FROM spins
        ORDER BY played_at DESC, id DESC
        LIMIT 100
    """).fetchall()

    winners = conn.execute("""
        SELECT * FROM spins
        WHERE claim_code IS NOT NULL
        ORDER BY played_at DESC, id DESC
        LIMIT 100
    """).fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        recent_rows=recent_rows,
        winners=winners,
        today=today_display()
    )


@app.post("/admin/redeem/<int:spin_id>")
@admin_required
def admin_redeem(spin_id: int):
    conn = get_db()
    conn.execute("UPDATE spins SET redeemed = 1 WHERE id = ?", (spin_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))


@app.get("/admin/export.csv")
@admin_required
def admin_export():
    conn = get_db()
    rows = conn.execute("""
        SELECT id, employee_id, spin_date, result_type, title, message, claim_code, power, redeemed, played_at
        FROM spins
        ORDER BY played_at DESC, id DESC
    """).fetchall()
    conn.close()

    lines = [
        "id,employee_id,spin_date,result_type,title,message,claim_code,power,redeemed,played_at"
    ]
    for row in rows:
        vals = [
            row["id"], row["employee_id"], row["spin_date"], row["result_type"],
            row["title"], row["message"], row["claim_code"] or "",
            row["power"], row["redeemed"], row["played_at"]
        ]
        escaped = []
        for v in vals:
            s = str(v).replace('"', '""')
            escaped.append(f'"{s}"')
        lines.append(",".join(escaped))

    csv_text = "\n".join(lines)
    filename = f"lucky-wheel-export-{today_key()}.csv"
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/healthz")
def healthz():
    return {"ok": True, "db_exists": DB_PATH.exists()}


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)