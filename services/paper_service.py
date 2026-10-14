from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from models import SystemSetting

DEFAULT_SETTINGS: Dict[str, float] = {
    "empty_distance_mm": 160.0,
    "roll_thickness_mm": 110.0,
    "sensor_offset_mm": 40.0,
    "warn_low_cm": 1.5,
    "warn_low_uses": 60.0,
    "warn_mid_cm": 1.0,
    "warn_mid_uses": 35.0,
    "warn_empty_cm": 0.5,
    "warn_empty_uses": 15.0,
}

# Cached in-memory settings for ultra-fast lookup during high-frequency sensor reports
_cached_settings: Dict[str, float] = dict(DEFAULT_SETTINGS)

def load_settings_from_db(db: Optional[Session] = None) -> Dict[str, float]:
    """Load settings from database into memory cache, inserting defaults if missing"""
    global _cached_settings
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        updated = False
        for k, default_val in DEFAULT_SETTINGS.items():
            row = db.query(SystemSetting).filter(SystemSetting.key == k).first()
            if not row:
                row = SystemSetting(key=k, value=str(default_val))
                db.add(row)
                updated = True
                _cached_settings[k] = default_val
            else:
                try:
                    _cached_settings[k] = float(row.value)
                except ValueError:
                    _cached_settings[k] = default_val
        if updated:
            db.commit()
    except Exception as e:
        print(f"[PaperService] Warning loading settings: {e}")
    finally:
        if close_db:
            db.close()
    return dict(_cached_settings)

def get_paper_settings() -> Dict[str, float]:
    """Get current active settings"""
    return dict(_cached_settings)

def update_paper_settings(db: Session, new_settings: Dict[str, float]) -> Dict[str, float]:
    """Update settings in database and in-memory cache"""
    global _cached_settings
    for k, v in new_settings.items():
        if k in DEFAULT_SETTINGS:
            float_val = float(v)
            _cached_settings[k] = float_val
            row = db.query(SystemSetting).filter(SystemSetting.key == k).first()
            if not row:
                row = SystemSetting(key=k, value=str(float_val))
                db.add(row)
            else:
                row.value = str(float_val)
    db.commit()
    return dict(_cached_settings)

def _estimate_uses(thick_cm: float, cfg: Dict[str, float]) -> int:
    """Nội suy số lượt dùng dựa trên độ dày cuộn giấy (cm)"""
    warn_empty_cm = cfg.get("warn_empty_cm", 0.5)
    warn_empty_uses = cfg.get("warn_empty_uses", 15.0)
    warn_mid_cm = cfg.get("warn_mid_cm", 1.0)
    warn_mid_uses = cfg.get("warn_mid_uses", 35.0)
    warn_low_cm = cfg.get("warn_low_cm", 1.5)
    warn_low_uses = cfg.get("warn_low_uses", 60.0)

    if thick_cm <= 0.0:
        return 0
    if thick_cm <= warn_empty_cm:
        return round((thick_cm / max(0.01, warn_empty_cm)) * warn_empty_uses)
    if thick_cm <= warn_mid_cm:
        span_cm = max(0.01, warn_mid_cm - warn_empty_cm)
        span_uses = warn_mid_uses - warn_empty_uses
        return round(warn_empty_uses + ((thick_cm - warn_empty_cm) / span_cm) * span_uses)
    if thick_cm <= warn_low_cm:
        span_cm = max(0.01, warn_low_cm - warn_mid_cm)
        span_uses = warn_low_uses - warn_mid_uses
        return round(warn_mid_uses + ((thick_cm - warn_mid_cm) / span_cm) * span_uses)
    # thick_cm > warn_low_cm: mỗi 0.5 cm tiếp theo được ~25 lần
    return round(warn_low_uses + ((thick_cm - warn_low_cm) / 0.5) * 25.0)

def calculate_paper_metrics(distance_mm: Optional[float], sensor_status: int = 0) -> Dict[str, Any]:
    """
    Phân tích từ khoảng cách cảm biến ToF (distance_mm):
    - empty_dist_mm: khoảng cách từ cảm biến tới đáy khi hết giấy (mặc định 140 mm)
    - roll_thickness_mm: độ dày cuộn giấy lúc đầy (mặc định 110 mm)
    - thick_mm = empty_dist - distance_mm (độ dày thực tế của giấy)
    """
    cfg = _cached_settings
    empty_dist = cfg.get("empty_distance_mm", 140.0)
    roll_thick = cfg.get("roll_thickness_mm", 110.0)
    warn_low_cm = cfg.get("warn_low_cm", 1.5)
    warn_empty_cm = cfg.get("warn_empty_cm", 0.5)

    if distance_mm is None or sensor_status != 0 or distance_mm < 0:
        return {
            "distance_mm": distance_mm,
            "remaining_thickness_mm": 0.0,
            "remaining_thickness_cm": 0.0,
            "paper_level": 0.0,
            "estimated_uses": 0,
            "status": "EMPTY"
        }

    sensor_offset = cfg.get("sensor_offset_mm", 0.0)
    adjusted_dist = max(0.0, float(distance_mm) - sensor_offset)

    # Bề mặt cuộn giấy khi đầy cách cảm biến: full_dist = empty_dist - roll_thick
    full_dist = max(0.0, empty_dist - roll_thick)

    if adjusted_dist <= full_dist:
        thick_mm = roll_thick
    elif adjusted_dist >= empty_dist:
        thick_mm = 0.0
    else:
        thick_mm = empty_dist - adjusted_dist

    thick_cm = round(thick_mm / 10.0, 2)
    percent = round(min(100.0, max(0.0, (thick_mm / roll_thick) * 100.0)), 1) if roll_thick > 0 else 0.0
    est_uses = _estimate_uses(thick_cm, cfg)

    # Đánh giá trạng thái cảnh báo theo quy định:
    # - > warn_low_cm (1.5 cm): Không cần cảnh báo (OK)
    # - <= warn_low_cm (1.5 cm): Cảnh báo sắp hết (LOW)
    # - <= warn_empty_cm (0.5 cm): Cảnh báo hết giấy (EMPTY)
    if thick_cm <= warn_empty_cm:
        status = "EMPTY"
    elif thick_cm <= warn_low_cm:
        status = "LOW"
    else:
        status = "OK"

    return {
        "distance_mm": round(adjusted_dist, 1),
        "raw_distance_mm": round(float(distance_mm), 1),
        "sensor_offset_mm": round(sensor_offset, 1),
        "remaining_thickness_mm": round(thick_mm, 1),
        "remaining_thickness_cm": thick_cm,
        "paper_level": percent,
        "estimated_uses": est_uses,
        "status": status
    }

def calculate_metrics_from_percent(paper_level: float) -> Dict[str, Any]:
    """Helper để tính độ dày và số lượt dùng từ paper_level (%) đã lưu"""
    cfg = _cached_settings
    roll_thick = cfg.get("roll_thickness_mm", 110.0)
    thick_mm = (max(0.0, min(100.0, float(paper_level or 0.0))) / 100.0) * roll_thick
    thick_cm = round(thick_mm / 10.0, 2)
    est_uses = _estimate_uses(thick_cm, cfg)

    return {
        "remaining_thickness_mm": round(thick_mm, 1),
        "remaining_thickness_cm": thick_cm,
        "estimated_uses": est_uses
    }
