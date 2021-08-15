from typing import List

import pytools.htmldump as htmldump


def __html() -> str:
    return """<html>
<head>
<meta charset="utf-8"/>
<title>planesphere</title>
</head>
<body>
<h1 id="constellation">Virgo</h1>
<p id="alpha">Spica</p>
<p id="beta">Zavijava</p>
<p id="gamma">Porrima</p>
</body>
</html>"""


def __htmltsv() -> List[str]:
    return [
        "start_tag\thtml\t[]",
        "data\t",
        "start_tag\thead\t[]",
        "data\t",
        'startend_log\tmeta\t[["charset","utf-8"]]',
        "data\t",
        "start_tag\ttitle\t[]",
        "data\tplanesphere",
        "end_tag\ttitle",
        "data\t",
        "end_tag\thead",
        "data\t",
        "start_tag\tbody\t[]",
        "data\t",
        'start_tag\th1\t[["id","constellation"]]',
        "data\tVirgo",
        "end_tag\th1",
        "data\t",
        'start_tag\tp\t[["id","alpha"]]',
        "data\tSpica",
        "end_tag\tp",
        "data\t",
        'start_tag\tp\t[["id","beta"]]',
        "data\tZavijava",
        "end_tag\tp",
        "data\t",
        'start_tag\tp\t[["id","gamma"]]',
        "data\tPorrima",
        "end_tag\tp",
        "data\t",
        "end_tag\tbody",
        "data\t",
        "end_tag\thtml",
        "data\t",
    ]


def test_run_tsv():
    it = ["{}\n".format(x) for x in __html().split("\n")]  # keep newline
    got = list(htmldump.Arguments(source=it, as_json=False).runner().run())
    assert len(got) == len(__htmltsv())
    assert all(g == w for g, w in zip(got, __htmltsv()))


def __htmljson() -> str:
    return """{"kind":"start_tag","tag":"html","attrs":[]}
{"kind":"data","data":""}
{"kind":"start_tag","tag":"head","attrs":[]}
{"kind":"data","data":""}
{"kind":"startend_log","tag":"meta","attrs":[["charset","utf-8"]]}
{"kind":"data","data":""}
{"kind":"start_tag","tag":"title","attrs":[]}
{"kind":"data","data":"planesphere"}
{"kind":"end_tag","tag":"title"}
{"kind":"data","data":""}
{"kind":"end_tag","tag":"head"}
{"kind":"data","data":""}
{"kind":"start_tag","tag":"body","attrs":[]}
{"kind":"data","data":""}
{"kind":"start_tag","tag":"h1","attrs":[["id","constellation"]]}
{"kind":"data","data":"Virgo"}
{"kind":"end_tag","tag":"h1"}
{"kind":"data","data":""}
{"kind":"start_tag","tag":"p","attrs":[["id","alpha"]]}
{"kind":"data","data":"Spica"}
{"kind":"end_tag","tag":"p"}
{"kind":"data","data":""}
{"kind":"start_tag","tag":"p","attrs":[["id","beta"]]}
{"kind":"data","data":"Zavijava"}
{"kind":"end_tag","tag":"p"}
{"kind":"data","data":""}
{"kind":"start_tag","tag":"p","attrs":[["id","gamma"]]}
{"kind":"data","data":"Porrima"}
{"kind":"end_tag","tag":"p"}
{"kind":"data","data":""}
{"kind":"end_tag","tag":"body"}
{"kind":"data","data":""}
{"kind":"end_tag","tag":"html"}
{"kind":"data","data":""}"""


def test_run_json():
    it = ["{}\n".format(x) for x in __html().split("\n")]  # keep newline
    got = list(htmldump.Arguments(source=it).runner().run())
    assert "\n".join(got) == __htmljson()
