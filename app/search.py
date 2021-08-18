from flask import current_app


def add_to_index(index, model):
    """This function addes an object to the given index."""

    # return None if the elasticsearch url is not configured
    if not current_app.elasticsearch:
        return

    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)

    current_app.elasticsearch.index(index=index, id=model.id, 
                                    body=payload)


def remove_from_index(index, model):
    """This function removes an object from the given index."""

    if not current_app.elasticsearch:
        return 
    current_app.elasticsearch.delete(index=index, id=model.id)


def query_index(index, query, page, per_page):
    """
    This function searches for matched objects given the search text and the 
    name of the index to search from.
    """

    if not current_app.elasticsearch:
        return [], 0

    # perform search via elasticsearch
    search = current_app.elasticsearch.search(index=index, 
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}}, 
              'from': (page - 1), 'size': per_page})

    total = search['hits']['total']['value']
    ids = [int(hit['_id']) for hit in search['hits']['hits']]

    return ids, total
    