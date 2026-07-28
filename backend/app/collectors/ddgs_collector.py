from ddgs import DDGS


def is_relevant(
    result,
    topic
):

    text = (
        result.get("title", "")
        +
        result.get("body", "")
    ).lower()

    topic_words = [
        word
        for word in topic.lower().split()
        if len(word) > 2
    ]

    return any(
        word in text
        for word in topic_words
    )


class DDGSCollector:

    async def collect(
        self,
        query: str,
        topic: str
    ):

        try:

            with DDGS() as ddgs:

                results = list(
                    ddgs.text(
                        query,
                        max_results=10
                    )
                )

            normalized_results = []

            for result in results:

                if not is_relevant(
                    result,
                    topic
                ):
                    continue

                normalized_results.append(
                    {
                        "source": "ddgs",
                        "title": result.get(
                            "title",
                            ""
                        ),
                        "url": result.get(
                            "href",
                            ""
                        ),
                        "snippet": result.get(
                            "body",
                            ""
                        )
                    }
                )

            return normalized_results

        except Exception as e:

            print(
                "DDGS ERROR:",
                str(e)
            )

            return []
        #comment
