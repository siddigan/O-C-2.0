import json

from app.db.session import SessionLocal
from app.models.models import Company


def main() -> None:
    db = SessionLocal()
    names = json.loads(open("app/config/companies.seed.json", encoding="utf-8").read())
    for idx, name in enumerate(names, start=1):
        exists = db.query(Company).filter(Company.name == name).first()
        if exists:
            continue
        db.add(Company(name=name, priority=max(1, 10 - (idx // 8))))
    db.commit()
    db.close()
    print(f"Seeded {len(names)} companies.")


if __name__ == "__main__":
    main()
