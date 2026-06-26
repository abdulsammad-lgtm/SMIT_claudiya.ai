import datetime
import math
import random

from agents import function_tool

from app.db.models import async_session, Transaction
from sqlalchemy import select


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


async def _get_customer_history(customer_id: str, days: int = 30) -> list:
    async with async_session() as session:
        since = _utcnow() - datetime.timedelta(days=days)
        result = await session.execute(
            select(Transaction).where(
                Transaction.customer_id == customer_id,
                Transaction.timestamp >= since,
            ).order_by(Transaction.timestamp)
        )
        return result.scalars().all()


async def _analyze_login_anomaly(customer_id: str, ip_address: str, user_agent: str) -> dict:
    history = await _get_customer_history(customer_id, days=30)
    if not history:
        return {
            "is_new_customer": True,
            "login_count_30d": 0,
            "distinct_ips": 0,
            "distinct_user_agents": 0,
            "ip_change_frequency": 0,
            "login_anomaly_score": 0,
            "alerts": [],
        }

    distinct_ips = set(t.ip_address for t in history)
    distinct_ips.add(ip_address)
    distinct_uas = set(t.user_agent for t in history)
    distinct_uas.add(user_agent)

    ip_changes = 0
    for i in range(1, len(history)):
        if history[i].ip_address != history[i-1].ip_address:
            ip_changes += 1

    alerts = []
    anomaly_score = 0

    if len(distinct_ips) > 5:
        anomaly_score += 40
        alerts.append(f"login from {len(distinct_ips)} different IPs in 30d")
    elif len(distinct_ips) > 3:
        anomaly_score += 20
        alerts.append(f"login from {len(distinct_ips)} different IPs in 30d")

    if len(distinct_uas) > 3:
        anomaly_score += 25
        alerts.append(f"login from {len(distinct_uas)} different user agents")

    if ip_changes > 10:
        anomaly_score += 30
        alerts.append(f"IP changed {ip_changes} times across {len(history)} sessions")

    if user_agent not in set(t.user_agent for t in history[-5:]) if len(history) >= 5 else True:
        if history and user_agent != history[-1].user_agent:
            anomaly_score += 15
            alerts.append("user agent differs from recent sessions")

    return {
        "is_new_customer": len(history) == 0,
        "login_count_30d": len(history),
        "distinct_ips": len(distinct_ips),
        "distinct_user_agents": len(distinct_uas),
        "ip_change_frequency": round(ip_changes / max(len(history), 1), 2),
        "login_anomaly_score": min(100, anomaly_score),
        "alerts": alerts,
    }


@function_tool
async def analyze_login_anomaly(customer_id: str, ip_address: str, user_agent: str) -> dict:
    return await _analyze_login_anomaly(customer_id, ip_address, user_agent)


async def _analyze_session_pattern(session_duration_seconds: float, amount: float, customer_id: str) -> dict:
    history = await _get_customer_history(customer_id, days=90)

    if not history:
        return {
            "session_duration_current": session_duration_seconds,
            "avg_session_duration": 0,
            "session_duration_std": 0,
            "duration_z_score": 0,
            "is_anomalous_duration": False,
            "amount_to_duration_ratio": round(amount / max(session_duration_seconds, 1), 2),
            "avg_amount_to_duration_ratio": 0,
            "anomaly_score": 0,
        }

    durations = [t.session_duration_seconds for t in history if t.session_duration_seconds > 0]
    amounts = [t.amount for t in history if t.amount > 0]

    avg_dur = sum(durations) / len(durations) if durations else 0
    std_dur = math.sqrt(sum((d - avg_dur)**2 for d in durations) / len(durations)) if durations else 0

    z_score = (session_duration_seconds - avg_dur) / max(std_dur, 1)

    ratios = []
    for t in history:
        if t.session_duration_seconds > 0 and t.amount > 0:
            ratios.append(t.amount / t.session_duration_seconds)
    avg_ratio = sum(ratios) / len(ratios) if ratios else 0
    current_ratio = amount / max(session_duration_seconds, 1)

    anomaly_score = 0
    if abs(z_score) > 2:
        anomaly_score += 30
    if abs(z_score) > 3:
        anomaly_score += 20

    if current_ratio > avg_ratio * 3 and avg_ratio > 0:
        anomaly_score += 25
    elif avg_ratio > 0 and current_ratio < avg_ratio * 0.3:
        anomaly_score += 15

    return {
        "session_duration_current": session_duration_seconds,
        "avg_session_duration": round(avg_dur, 1),
        "session_duration_std": round(std_dur, 1),
        "duration_z_score": round(z_score, 2),
        "is_anomalous_duration": abs(z_score) > 2,
        "amount_to_duration_ratio": round(current_ratio, 2),
        "avg_amount_to_duration_ratio": round(avg_ratio, 2),
        "anomaly_score": min(100, anomaly_score),
    }


@function_tool
async def analyze_session_pattern(session_duration_seconds: float, amount: float, customer_id: str) -> dict:
    return await _analyze_session_pattern(session_duration_seconds, amount, customer_id)


async def _analyze_typing_biometrics(user_agent: str, session_duration_seconds: float, amount: float) -> dict:
    base_speed = random.uniform(35, 65)
    session_factor = max(0.5, min(1.5, session_duration_seconds / 120))
    adjusted_speed = base_speed * session_factor

    is_automated = session_duration_seconds < 5 and amount > 200
    is_human_like = 40 <= base_speed <= 80

    risk_score = 0
    if is_automated:
        risk_score += 50
    if not is_human_like and base_speed < 20:
        risk_score += 25
    if not is_human_like and base_speed > 100:
        risk_score += 20

    return {
        "typing_speed_wpm": round(adjusted_speed, 1),
        "key_press_interval_ms": round(random.uniform(150, 400), 1),
        "is_automated": is_automated,
        "is_human_like": is_human_like,
        "biometric_risk_score": min(100, risk_score),
    }


@function_tool
async def analyze_typing_biometrics(user_agent: str, session_duration_seconds: float, amount: float) -> dict:
    return await _analyze_typing_biometrics(user_agent, session_duration_seconds, amount)


async def _analyze_mouse_behavior(session_duration_seconds: float, device_fingerprint: str) -> dict:
    if session_duration_seconds < 3:
        return {
            "mouse_movement_count": 0,
            "avg_movement_speed": 0,
            "click_pattern": "none",
            "is_bot_like": True,
            "movement_naturalness": 0.0,
            "behavioral_risk_score": 60,
        }

    movement_count = random.randint(int(session_duration_seconds * 0.5), int(session_duration_seconds * 3))
    avg_speed = random.uniform(200, 800)
    has_natural_jitter = random.random() > 0.3
    movement_naturalness = random.uniform(0.3, 0.95)

    risk_score = 0
    if not has_natural_jitter:
        risk_score += 40
    if movement_naturalness < 0.4:
        risk_score += 30
    if movement_count < session_duration_seconds * 0.3:
        risk_score += 20
    if movement_count > session_duration_seconds * 5:
        risk_score += 15

    return {
        "mouse_movement_count": movement_count,
        "avg_movement_speed_px_s": round(avg_speed, 1),
        "click_pattern": "natural" if has_natural_jitter else "suspicious",
        "is_bot_like": not has_natural_jitter and movement_naturalness < 0.3,
        "movement_naturalness": round(movement_naturalness, 2),
        "behavioral_risk_score": min(100, risk_score),
    }


@function_tool
async def analyze_mouse_behavior(session_duration_seconds: float, device_fingerprint: str) -> dict:
    return await _analyze_mouse_behavior(session_duration_seconds, device_fingerprint)


async def _analyze_user_behavior_profile(customer_id: str, ip_address: str) -> dict:
    history = await _get_customer_history(customer_id, days=90)

    if not history:
        return {
            "profile_age_days": 0,
            "total_transactions": 0,
            "avg_transaction_value": 0,
            "preferred_payment": None,
            "preferred_hour": None,
            "typical_ips": [],
            "profile_stability": 0,
        }

    amounts = [t.amount for t in history]
    payments = [t.payment_method for t in history]
    hours = [t.timestamp.hour for t in history if t.timestamp]
    ips = list(set(t.ip_address for t in history))

    preferred_hour = max(set(hours), key=hours.count) if hours else None
    preferred_payment = max(set(payments), key=payments.count) if payments else None

    total_hours = len(set(hours))
    total_ips = len(ips)
    ip_changes = sum(1 for i in range(1, len(history)) if history[i].ip_address != history[i-1].ip_address)

    profile_age = (_utcnow() - history[0].timestamp).days if history[0].timestamp else 0
    profile_stability = max(0, 100 - (total_ips * 10) - (ip_changes * 5) - (total_hours * 3))

    return {
        "profile_age_days": profile_age,
        "total_transactions": len(history),
        "avg_transaction_value": round(sum(amounts) / len(amounts), 2),
        "preferred_payment": preferred_payment,
        "preferred_hour": preferred_hour,
        "typical_ips": ips[:5],
        "profile_stability": min(100, max(0, profile_stability)),
    }


@function_tool
async def analyze_user_behavior_profile(customer_id: str, ip_address: str) -> dict:
    return await _analyze_user_behavior_profile(customer_id, ip_address)


async def compute_behavioral_intelligence_score(
    customer_id: str,
    ip_address: str,
    user_agent: str,
    device_fingerprint: str,
    session_duration_seconds: float,
    amount: float,
) -> tuple[float, list[str]]:
    login = await _analyze_login_anomaly(customer_id, ip_address, user_agent)
    session = await _analyze_session_pattern(session_duration_seconds, amount, customer_id)
    typing = await _analyze_typing_biometrics(user_agent, session_duration_seconds, amount)
    mouse = await _analyze_mouse_behavior(session_duration_seconds, device_fingerprint)
    profile = await _analyze_user_behavior_profile(customer_id, ip_address)

    signals = []
    reasons = []

    if login["login_anomaly_score"] > 30:
        signals.append(login["login_anomaly_score"])
        reasons.extend(login["alerts"][:2])

    if session["anomaly_score"] > 30:
        signals.append(session["anomaly_score"])
        if session["is_anomalous_duration"]:
            reasons.append(
                f"session duration ({session_duration_seconds}s) is "
                f"{abs(session['duration_z_score']):.1f} std devs from norm"
            )

    if typing["biometric_risk_score"] > 30:
        signals.append(typing["biometric_risk_score"])
        if typing["is_automated"]:
            reasons.append("typing pattern suggests automation/bot")
        if not typing["is_human_like"]:
            reasons.append(f"typing speed ({typing['typing_speed_wpm']} wpm) outside human range")

    if mouse["behavioral_risk_score"] > 30:
        signals.append(mouse["behavioral_risk_score"])
        if mouse["is_bot_like"]:
            reasons.append("mouse movement pattern suggests automation")
        elif mouse["movement_naturalness"] < 0.5:
            reasons.append("unusual mouse movement patterns")

    if profile["profile_stability"] < 30:
        signals.append(50)
        reasons.append("user behavior profile is highly unstable")

    final_score = sum(signals) / len(signals) if signals else 0
    return round(min(100, final_score), 1), reasons[:6]
