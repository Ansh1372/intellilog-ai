from backend.router import LogRouter


router = LogRouter()

test_logs = [

    "authentication failed for admin",

    "database connection timeout on postgres",

    "gateway request exceeded timeout limit",

    "filesystem full on production server",

    "strange unknown distributed system failure"
]


for log in test_logs:

    result = router.process_log(log)

    print("\nLOG:")
    print(log)

    print("RESULT:")
    print(result)
