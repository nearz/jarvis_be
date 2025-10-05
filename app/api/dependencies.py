from fastapi import Request


def get_app_graph(req: Request):
    return req.app.state.graph


def get_graph_saver(req: Request):
    return req.app.state.saver
