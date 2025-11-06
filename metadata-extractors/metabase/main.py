from extractor import MetabaseExtractor


def run():
    mb = MetabaseExtractor()
    collections = mb.fetch_collections()
    dashboards = mb.fetch_dashboards()
    cards_total, questions, models, metrics = mb.fetch_cards_and_counts()
    segments = mb.fetch_segments()
    snippets = mb.fetch_snippets()

    print(
        f"Collections: {collections} | Dashboards: {dashboards} | "
        f"Questions: {questions} | Models: {models} | Metrics: {metrics} | "
        f"Segments: {segments} | Snippets: {snippets}"
    )


if __name__ == "__main__":
    run()
