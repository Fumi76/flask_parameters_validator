from flask import Flask, request

app = Flask(__name__, static_url_path='/static')


@app.route('/query_params')
def query_params():
    p1 = request.args['param1']
    print(p1, type(p1)) # str
    p2 = request.args.get("param1")
    print(p2, type(p2)) # str

    if 'param1' in request.form:
        print('form', request.form['param1'])

    print('request.args', type(request.args))
    # request.args <class 'werkzeug.datastructures.ImmutableMultiDict'>

    return 'Hello to the World of Flask!'
# クエリパラメータ、文字列
# formからは取得できない


@app.route('/form', methods=['POST'])
def post_form():
    p1 = request.form['text1']
    print(p1, type(p1)) # str
    p2 = request.form.get("text1")
    print(p2, type(p2)) # str

    if 'text1' in request.args:
        v2 = request.args['text1']
        print("args", v2)

    print('request.form', type(request.form))
    # request.form <class 'werkzeug.datastructures.ImmutableMultiDict'>
    # multipart/form-dataもx-www-form-urlencodedどちらも上記

    print('request', type(request))
    # request <class 'werkzeug.local.LocalProxy'>

    return 'Hello to the World of Flask!'
# Form形式、文字列
# request.argsからは取得できない
# application/x-www-form-urlencodedとmultipart/form-dataどちらでもrequest.argsからは取得できない


@app.route('/file', methods=['POST'])
def upload_file():
    file = request.files['myfile']
    print(file)
    p1 = request.form['text1']
    print(p1, type(p1)) # str
    p2 = request.form.get("text1")
    print(p2, type(p2)) # str

    if 'myfile' in request.form:
        print('form', request.form['myfile'])

    if 'myfile' in request.args:
        v2 = request.args['myfile']
        print("args", v2)

    print('request.files', type(request.files))
    # request.files <class 'werkzeug.datastructures.ImmutableMultiDict'>

    return 'Hello to the World of Flask!'
# Form形式のmultipartも文字列
# ファイルはrequest.filesからしか取得できない


@app.route('/json', methods=['POST'])
def json():
    # ちなみに不正なJSONを送るとこの手前で400が返る（エラーメッセージ付き）
    j = request.json # つまり、これはすでにパースできた後
    # 自前でパースするなら以下
    # data = request.data.decode('utf-8')
    # data = json.loads(data)
    print(j["key1"], type(j["key1"])) # int
    print(j["key2"], type(j["key2"])) # str
    print(j["key3"], type(j["key3"])) # bool
    return j
# JSON文字列の場合、パース後は型が分かれる

# 文字列の場合は、必要に応じて型を変換しつつ、値を検証することになる
# JSONの場合は、パースできたか、できなかったかで１つ分岐があり、
# パースで来た場合は、そのJSONデータの型、値を調べることになる
# 基本的には文字列から必要な型への変換は不要

