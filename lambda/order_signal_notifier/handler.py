import json


def lambda_handler(event, _context):
    print("Lambda triggered by SQS")
    print(json.dumps(event, default=str))

    processed = []
    for record in event.get("Records", []):
        entry = {
            "message_id": record.get("messageId"),
            "body": record.get("body"),
            "attributes": record.get("attributes", {}),
            "message_attributes": record.get("messageAttributes", {}),
        }
        print(json.dumps(entry, default=str))
        processed.append(entry)

    return {
        "processed_records": len(processed),
        "messages": processed,
    }
