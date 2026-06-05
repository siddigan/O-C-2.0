from app.db.session import SessionLocal
from app.models.models import Company

companies = [
    ("Adobe", "https://www.adobe.com/careers.html"),
    ("Airbnb", "https://careers.airbnb.com/"),
    ("Airbus", "https://www.airbus.com/en/careers"),
    ("Akamai Technologies", "https://www.akamai.com/careers"),
    ("Amazon", "https://www.amazon.jobs/"),
    ("American Express", "https://www.americanexpress.com/en-us/careers/"),
    ("Apple", "https://www.apple.com/careers/"),
    ("Atlassian", "https://www.atlassian.com/company/careers"),
    ("BNY Mellon", "https://www.bnymellon.com/careers"),
    ("Chargebee", "https://www.chargebee.com/careers/"),
    ("Citi Bank", "https://jobs.citi.com/"),
    ("Coinbase", "https://www.coinbase.com/careers"),
    ("DP World", "https://www.dpworld.com/careers"),
    ("EPAM Systems", "https://www.epam.com/careers"),
    ("Goldman Sachs", "https://www.goldmansachs.com/careers"),
    ("Google", "https://careers.google.com/"),
    ("Harness", "https://www.harness.io/careers"),
    ("IBM", "https://www.ibm.com/careers"),
    ("Indeed", "https://www.indeed.jobs/"),
    ("InMobi", "https://www.inmobi.com/company/careers"),
    ("Intel", "https://jobs.intel.com/"),
    ("Intuit", "https://www.intuit.com/careers/"),
    ("JPMC (JPMorgan Chase)", "https://careers.jpmorgan.com/"),
    ("LinkedIn", "https://careers.linkedin.com/"),
    ("Mastercard", "https://careers.mastercard.com/"),
    ("McKinsey", "https://www.mckinsey.com/careers"),
    ("Media.net", "https://careers.media.net/"),
    ("Meta", "https://www.metacareers.com/"),
    ("Microsoft", "https://careers.microsoft.com/"),
    ("MindTickle", "https://www.mindtickle.com/careers/"),
    ("Morgan Stanley", "https://www.morganstanley.com/people-opportunities"),
    ("NVIDIA", "https://www.nvidia.com/en-us/about-nvidia/careers/"),
    ("Oracle", "https://careers.oracle.com/"),
    ("PayPal", "https://www.paypal.com/careers"),
    ("Paytm", "https://paytm.com/careers"),
    ("PhonePe", "https://www.phonepe.com/careers/"),
    ("Philips", "https://www.careers.philips.com/"),
    ("Postman", "https://www.postman.com/company/careers/"),
    ("Publicis Sapient", "https://careers.publicissapient.com/"),
    ("Pure Storage", "https://www.purestorage.com/company/careers.html"),
    ("Qualcomm", "https://www.qualcomm.com/company/careers"),
    ("SAP Labs", "https://jobs.sap.com/"),
    ("Samsung", "https://www.samsung.com/us/careers/"),
    ("ServiceNow", "https://careers.servicenow.com/"),
    ("Sprinklr", "https://www.sprinklr.com/careers/"),
    ("Swiggy", "https://careers.swiggy.com/"),
    ("Target", "https://corporate.target.com/careers"),
    ("Tekion Corp", "https://tekion.com/careers"),
    ("Tesla", "https://www.tesla.com/careers"),
    ("ThoughtSpot", "https://www.thoughtspot.com/careers"),
    ("Tower Research Capital", "https://www.tower-research.com/careers"),
    ("Uber", "https://www.uber.com/careers/"),
    ("VMware", "https://careers.vmware.com/"),
    ("Walmart", "https://careers.walmart.com/"),
    ("Wells Fargo", "https://www.wellsfargo.com/about/careers/"),
    ("Western Digital", "https://jobs.westerndigital.com/"),
    ("Zeta", "https://www.zeta.tech/careers"),
    ("Zoho", "https://www.zoho.com/careers.html"),
    ("Idfc", "https://www.idfcfirstbank.com/careers"),
    ("Koch", "https://jobs.kochcareers.com/"),
    ("Maersk", "https://www.maersk.com/careers"),
    ("Jane Street", "https://www.janestreet.com/join-jane-street/open-roles/"),
    ("Citadel", "https://www.citadel.com/careers/open-positions/"),
    ("Citadel Securities", "https://www.citadelsecurities.com/careers/open-opportunities/"),
    ("Hudson River Trading", "https://www.hudsonrivertrading.com/careers/"),
    ("Two Sigma", "https://www.twosigma.com/careers/"),
    ("D.E. Shaw", "https://www.deshaw.com/careers"),
    ("Jump Trading", "https://www.jumptrading.com/careers/"),
    ("Optiver", "https://optiver.com/working-at-optiver/career-opportunities/"),
    ("IMC Trading", "https://www.imc.com/us/careers/"),
    ("DRW", "https://drw.com/work-at-drw/"),
    ("Susquehanna International Group", "https://sig.com/careers/"),
    ("Five Rings", "https://fiverings.com/careers/"),
    ("Akuna Capital", "https://akunacapital.com/careers/"),
    ("Millennium Management", "https://www.mlp.com/careers/"),
    ("Point72", "https://careers.point72.com/"),
    ("Balyasny Asset Management", "https://www.bamfunds.com/careers/overview"),
    ("Bridgewater Associates", "https://www.bridgewater.com/careers/"),
    ("Schonfeld", "https://www.schonfeld.com/careers/"),
    ("Squarepoint Capital", "https://www.squarepoint-capital.com/careers"),
    ("Qube Research & Technologies", "https://www.qube-rt.com/careers/"),
    ("G-Research", "https://www.gresearch.com/careers/"),
    ("XTX Markets", "https://www.xtxmarkets.com/careers/"),
]

PRIORITY = 9
TOP_QUANT_HEDGE_FUNDS = {
    "Jane Street",
    "Citadel",
    "Citadel Securities",
    "Hudson River Trading",
    "Two Sigma",
    "D.E. Shaw",
    "Jump Trading",
    "Optiver",
    "IMC Trading",
    "DRW",
    "Susquehanna International Group",
    "Five Rings",
    "Akuna Capital",
    "Millennium Management",
    "Point72",
    "Balyasny Asset Management",
    "Bridgewater Associates",
    "Schonfeld",
    "Squarepoint Capital",
    "Qube Research & Technologies",
    "G-Research",
    "XTX Markets",
}

def main():
    db = SessionLocal()
    try:
        inserted = updated = 0
        for name, url in companies:
            priority = 10 if name in TOP_QUANT_HEDGE_FUNDS else PRIORITY
            company = db.query(Company).filter(Company.name == name).first()
            if company:
                company.priority = priority
                company.enabled = True
                company.career_url = url
                updated += 1
            else:
                company = Company(name=name, priority=priority, enabled=True, career_url=url)
                db.add(company)
                inserted += 1
        db.commit()
        print({"inserted": inserted, "updated": updated})
    finally:
        db.close()

if __name__ == "__main__":
    main()
