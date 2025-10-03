from fastapi import Request


def get_app_graph(req: Request):
    return req.app.state.graph
