# competitive_signals.py

def extract(evidence):

    launches = 0

    total_votes_per_day = 0

    total_comments_per_day = 0

    for item in evidence:

        if item["source"] == "producthunt":

            launches += 1

            total_votes_per_day += item.get(
                "votes_per_day",
                0
            )

            total_comments_per_day += item.get(
                "comments_per_day",
                0
            )

    avg_votes_per_day = 0

    if launches:

        avg_votes_per_day = (
            total_votes_per_day
            /
            launches
        )

    competition_score = min(
        100,
        int(
            launches * 2
            +
            avg_votes_per_day
        )
    )

    return {

        "launches":
        launches,

        "avg_votes_per_day":
        round(
            avg_votes_per_day,
            2
        ),

        "competition_score":
        competition_score
    }