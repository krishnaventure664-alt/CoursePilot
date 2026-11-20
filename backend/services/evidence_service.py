
def has_sufficient_evidence(search_results: list) -> bool:
    """
    Check whether retrieval returned usable text evidence.

    This is a basic availability check, not a calibrated
    relevance or factual-support verification system.
    """
    if not search_results:
        return False

    usable_chunks = [
        result
        for result in search_results
        if isinstance(result.get("text"), str)
        and result["text"].strip()
    ]

    return len(usable_chunks) >= 1
