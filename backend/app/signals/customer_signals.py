# customer_signals.py

def extract(evidence):

    discussion_volume = len(
        evidence
    )

    total_comments = 0

    for item in evidence:

        if item.get("source") =="youtube":

            total_comments += item.get(
                "comments",
                0
            )

    return {

        "discussion_volume":
        discussion_volume,

        "comment_volume":
        total_comments
    }