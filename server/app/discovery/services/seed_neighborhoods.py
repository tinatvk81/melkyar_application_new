from app.db.session import SessionLocal
from app.discovery.models.neighborhood import DiscoveryNeighborhood

SEED = [
    "اقبال", "لادن", "شهرآرا", "صیاد شیرازی", "حافظ", "صارمی", "هفت‌تیر",
    "پیروزی", "هاشمیه", "نیروهوایی", "هنرستان", "باهنر", "کوثر", "چهارراه چشمه",
    "ارشاد", "آزادگاه", "بهاران", "بهشت", "فلسطین", "گوهرشاد", "سجاد", "سرافرازان",
    "عبدالمطلب", "ابوذر", "قدس", "هدایت", "فکوری", "شهید مطهری",
    "فجر", "فاطمیه", "آبکوه", "رسالت", "وحید",
    "امیرالمومنین", "مهرآباد", "قائم",
    "فرهنگیان", "شهرک غرب", "دانشجو", "کارگران", "جاهد شهر", "طبرسی شمالی",
    "بهمن", "الهیه", "دانش آموز",
]


def run():
    db = SessionLocal()
    try:
        for name in SEED:
            exists = db.query(DiscoveryNeighborhood).filter_by(name=name).first()
            if not exists:
                db.add(DiscoveryNeighborhood(name=name))
        db.commit()
        print(f"{len(SEED)} محله بررسی/اضافه شد")
    finally:
        db.close()


if __name__ == "__main__":
    run()