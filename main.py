from flask import Flask, request, make_response
from validator import RequestParamsValidator
import json

app = Flask(__name__, static_url_path='/static')

spec = [{'param_name': 'hoge', 'src': 'form', 'required': True
             , 'type': 'integer', 'min_value': 0, 'max_value': 500
        }, {'param_name': 'foo', 'src': 'query', 'required': True
             , 'type': 'str', 'max': 5, 'min': 5
        }, {'param_name': 'key4', 'src': 'form', 'required': True
             , 'type': 'float', 'precision': 3, 'min_value': "0.001", 'max_value': '99.999'
        }, {'param_name': 'key5', 'src': 'json_body', 'required': True
             , 'type': 'integer', 'min_value': 0, 'max_value': 500
        }, {'param_name': 'key6', 'src': 'json_body', 'required': True
            # type を指定していないがrequired=Trueもありうる
        }, {'param_name': 'key7', 'src': 'json_body', 'required': True
            , 'type': 'float', 'precision': 3, 'min_value': "0.001", 'max_value': '99.999', 'convert_str': True
        }, {'param_name': 'key8', 'src': 'json_body'
            , 'type': 'str', 'max': 5, 'min': 5
        }, {'param_name': 'key9', 'src': 'form', 'indexed': True, 'required': True
            , 'type': 'integer', 'min_value': 0, 'max_value': 500
        }, {'param_name': 'key10', 'src': 'json_body', 'indexed': True
            , 'type': 'float', 'min_value': "0.001", 'max_value': "100"
        }, {'param_name': 'alpha', 'src': 'form', 'indexed': True
        },
        {'param_name': 'beta', 'src': 'form', 'indexed': True
        },
        {'type': 'required_params_in_same_index'
        , 'param_names': ['alpha', 'beta']
        },
        {'param_name': 'my_doc', 'src': 'form', 'required': True
         , 'type': 'file'
        },
        ]

validator = RequestParamsValidator(spec)


@app.route('/test', methods=['POST'])
def test():
    result = validator.validate(request)
    print("Errors")
    print(result[0])
    print("Type Converted Input params")
    print(vars(result[1]))
    response = make_response(json.dumps(result[0], ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=UTF-8'
    return response, 200


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


@app.route('/json_body', methods=['POST'])
def json_body():
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

