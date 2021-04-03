import copy
import decimal
import json
import re


class MockRequest:
    def __init__(self):
        self.args = {}
        self.form = {}
        self.files = {}
        self.data = b''
        self.json_body = {}

    def set_value(self, src, name, value):
        if src == 'form':
            self.form[name] = value
        elif src == 'query':
            self.args[name] = value
        elif src == 'files':
            self.files[name] = value
        elif src == 'json_body':
            self.json_body[name] = value
        else:
            raise Exception('不明なsrc ' + src)


class RequestParamsValidator:

    def __init__(self, spec):
        self.spec = spec

    # エントリ関数
    def validate(self, input_request):

        errors = []

        # src == json_bodyがある場合
        is_json_body = False
        is_json_body_required = False
        for item in self.spec:
            if is_json_body_required:
                break
            if item['src'] == 'json_body':
                is_json_body = True
                if 'required' in item and item['required']:
                    is_json_body_required = True

        type_converted = MockRequest()
        json_body = None

        if is_json_body:
            try:
                data = input_request.data.decode('utf-8')
                json_body = json.loads(data)
                type_converted.json_body = json_body
            except json.JSONDecodeError:
                if is_json_body_required:
                    errors.append("リクエストボディがJSON形式ではありません")
                    # この時点で返す
                    return errors, type_converted

        # 入力をコピー（チェックしない項目も含めて返す）、もしくはチェックした項目だけ返す TODO
        type_converted.form = copy.copy(input_request.form)
        type_converted.args = copy.copy(input_request.args)
        type_converted.files = copy.copy(input_request.files)

        indexed_params = []
        indexed_params_validation = []

        for item in self.spec:

            if 'type' in item and item['type'] == 'required_params_in_same_index':
                indexed_params_validation.append(item)
                # あとで検証は実行
                continue

            # 添え字付きのパラメータの場合
            if 'indexed' in item and item['indexed']:

                param_name = item['param_name']

                # 必須か
                is_required = False

                if 'types' in item:
                    validation_types = item['types']
                    for t in validation_types:
                        if t['type'] == 'required':
                            is_required = True
                            break

                p = re.compile(re.escape(param_name) + r'\[(.*)\]')
                p2 = re.compile(r'([0-9]+)')

                # ここでは収集だけする、あとで添え字でソートして検証実行

                if item['src'] == 'form':
                    cnt = 0
                    for key in input_request.form:
                        m = p.fullmatch(key)
                        if m is not None:
                            value = input_request.form[key]
                            idx = m.group(1)
                            m2 = p2.fullmatch(idx)
                            if m2 is None:
                                errors.append(param_name + "[x] (添え字付き)の添え字には整数を指定してください")
                                cnt += 1  # エラーを二重に出さないため
                            else:
                                indexed_params.append([int(m2.group(1)), key, value, item])
                                cnt += 1
                    if is_required and cnt == 0:
                        errors.append(param_name + "[x] (添え字付き)の指定は必須です")
                        continue

                elif item['src'] == 'query':
                    cnt = 0
                    for key in input_request.args:
                        m = p.fullmatch(key)
                        if m is not None:
                            value = input_request.args[key]
                            idx = m.group(1)
                            m2 = p2.fullmatch(idx)
                            if m2 is None:
                                errors.append(param_name + "[x] (添え字付き)の添え字には整数を指定してください")
                                cnt += 1 # エラーを二重に出さないため
                            else:
                                indexed_params.append([int(m2.group(1)), key, value, item])
                                cnt += 1
                    if is_required and cnt == 0:
                        errors.append(param_name + "[x] (添え字付き)の指定は必須です")
                        continue

                elif item['src'] == 'file':
                    cnt = 0
                    for key in input_request.files:
                        m = p.fullmatch(key)
                        if m is not None:
                            value = input_request.files[key]
                            idx = m.group(1)
                            m2 = p2.fullmatch(idx)
                            if m2 is None:
                                errors.append(param_name + "[x] (添え字付き)の添え字には整数を指定してください")
                                cnt += 1 # エラーを二重に出さないため
                            else:
                                indexed_params.append([int(m2.group(1)), key, value, item])
                                cnt += 1
                    if is_required and cnt == 0:
                        errors.append(param_name + "[x] (添え字付き)の指定は必須です")
                        continue
                elif item['src'] == 'json_body':
                    cnt = 0
                    for key in json_body:
                        m = p.fullmatch(key)
                        if m is not None:
                            value = json_body[key]
                            idx = m.group(1)
                            m2 = p2.fullmatch(idx)
                            if m2 is None:
                                errors.append(param_name + "[x] (添え字付き)の添え字には整数を指定してください")
                                cnt += 1 # エラーを二重に出さないため
                            else:
                                indexed_params.append([int(m2.group(1)), key, value, item])
                                cnt += 1
                    if is_required and cnt == 0:
                        errors.append(param_name + "[x] (添え字付き)の指定は必須です")
                        continue
                else:
                    raise Exception('不明なsrc '+str(item['src']))
            else:
                # 添え字なしパラメータ
                param_name = item['param_name']

                param_value = None

                if item['src'] == 'form':
                    if param_name in input_request.form:
                        param_value = input_request.form[param_name]
                elif item['src'] == 'query':
                    if param_name in input_request.args:
                        param_value = input_request.args[param_name]
                elif item['src'] == 'file':
                    if param_name in input_request.files:
                        param_value = input_request.files[param_name]
                elif item['src'] == 'json_body':
                    if param_name in json_body:
                        param_value = json_body[param_name]
                else:
                    raise Exception('不明なsrc ' + str(item['src']))

                self.validate_param(param_name, param_value, item, type_converted, errors)

        # 添え字番号でソート
        sorted(indexed_params, key=lambda x: x[0])
        print("paramsソート後", indexed_params)
        indexes = []
        indexed_params_map = {}
        for param in indexed_params:

            self.validate_param(param[1], param[2], param[3], type_converted, errors)

            if param[0] not in indexes:
                indexes.append(param[0])

            # item
            key = param[3]['param_name'] + '[' + str(param[0]) + ']'
            if key not in indexed_params_map:
                indexed_params_map[key] = []
                indexed_params_map[key].append(param[2])
            else:
                indexed_params_map[key].append(param[2])

        for validation in indexed_params_validation:
            if validation['type'] == 'required_params_in_same_index':
                p_names = validation['param_names']
                for idx in indexes:
                    existing_names = []
                    absent_names = []
                    for p_name in p_names:
                        key = p_name + '[' + str(idx) + ']'
                        if key not in indexed_params_map:
                            absent_names.append(key)
                        elif len(indexed_params_map[key]) == 0:
                            absent_names.append(key)
                        else:
                            has_value = False
                            for v in indexed_params_map[key]:
                                if v is not None and len(str(v).strip()) > 0:
                                    has_value = True
                                    break
                            if not has_value:
                                absent_names.append(key)
                            else:
                                existing_names.append(key)
                    if len(absent_names) > 0 and len(existing_names) > 0:
                        # 少なくとも１つはexisting_namesにあるはず
                        errors.append(", ".join(existing_names) + ' に対応する ' + ", ".join(absent_names) + ' が指定されていません')

        return errors, type_converted

    # １つのパラメータの検証
    def validate_param(self, param_name, param_value, item, type_converted, errors):

        is_required = False
        if 'required' in item and item['required']:
            is_required = True

        # 必須ではない項目は値が指定されていなければ検証しなくてよい
        if not is_required and (param_value is None or len(str(param_value).strip()) == 0):
            # 次の項目へ
            return

        converted_value = None
        is_error = False

        if 'type' not in item:
            # 型の指定はないが、必須チェックはある
            if is_required and (param_value is None or len(str(param_value.strip())) == 0):
                errors.append(param_name + "の指定は必須です。")
            return

        # 整数チェック
        if item['type'] == 'integer':

            if item['src'] == 'json_body':

                if is_required and param_value is None:
                    errors.append(param_name + "の指定は必須です。")
                    is_error = True
                elif type(param_value) is int:
                    pass
                elif type(param_value) is float:
                    if not param_value.is_integer():
                        errors.append(param_name + ' 整数を指定してください')
                        is_error = True
                elif type(param_value) is str:
                    if 'convert_str' in item and item['convert_str']:
                        try:
                            decimal_value = decimal.Decimal(param_value)
                            if not (decimal_value % 1 == 0):
                                errors.append(param_name + ' 整数を指定してください')
                                is_error = True
                            else:
                                converted_value = int(decimal_value)
                        except decimal.InvalidOperation:
                            errors.append(param_name + " 数値ではありません")
                            is_error = True
                    else:
                        errors.append(param_name + " 値が数値型ではありません")
                        is_error = True
                else:
                    errors.append(param_name + " 値が数値型ではありません")
                    is_error = True
            else:
                # json_body以外 (str型)

                if is_required and (param_value is None or len(param_value.strip()) == 0):
                    errors.append(param_name + "の指定は必須です。")
                    is_error = True

                elif type(param_value) is float and not param_value.is_integer(): # float型はありえないかもしれない
                    errors.append(param_name + " 整数ではありません")
                    is_error = True

                elif len(param_value.strip()) > 0:
                    try:
                        decimal_value = decimal.Decimal(param_value)
                        if decimal_value % 1 != 0:
                            errors.append(param_name + " の値が整数ではありません")
                            is_error = True
                        elif 'min_value' in item and decimal_value < decimal.Decimal(item['min_value']):
                            errors.append(param_name + " 最小値を下回っています" + str(item['min_value']))
                            is_error = True
                        elif 'max_value' in item and decimal_value > decimal.Decimal(item['max_value']):
                            errors.append(param_name + " 最大値を上回っています" + str(item['max_value']))
                            is_error = True
                        else:
                            converted_value = int(decimal_value)

                    except decimal.InvalidOperation:
                        errors.append(param_name + " の値が整数ではありません")
                        is_error = True

        # 小数点以下あり数値
        elif item['type'] == 'float':

            if item['src'] == 'json_body':

                if is_required and param_value is None:
                    errors.append(param_name + "の指定は必須です。")
                    is_error = True
                elif type(param_value) is float:
                    converted_value = decimal.Decimal(str(param_value))
                elif type(param_value) is int:
                    converted_value = decimal.Decimal(param_value)
                elif type(param_value) is str:
                    if 'convert_str' in item and item['convert_str']:
                        try:
                            decimal_value = decimal.Decimal(param_value)

                            if 'precision' in item:
                                s = str(decimal_value)
                                a = s.split(".")
                                if len(a) > 1 and len(a[1].rstrip("0")) > item['precision']:
                                    errors.append(param_name + "小数点以下は" + str(item['precision']) + 'までです')
                                    is_error = True

                            if 'min_value' in item and decimal_value < decimal.Decimal(item['min_value']):
                                errors.append(param_name + " 最小値を下回っています" + str(item['min_value']))
                                is_error = True
                            if 'max_value' in item and decimal_value > decimal.Decimal(item['max_value']):
                                errors.append(param_name + " 最大値を上回っています" + str(item['max_value']))
                                is_error = True

                            # float型に変換も選択肢としてあるが、今はDecimalを返す
                            converted_value = decimal_value

                        except decimal.InvalidOperation:
                            errors.append(param_name + " 数値ではありません")
                            is_error = True
                    else:
                        errors.append(param_name + " 値が数値型ではありません")
                        is_error = True
                else:
                    errors.append(param_name + " 値が数値型ではありません")
                    is_error = True

            else:
                # json_body以外 (str型のみ)
                if is_required and (param_value is None or len(param_value.strip()) == 0):
                    errors.append(param_name + "の指定は必須です。")
                    is_error = True

                elif len(param_value.strip()) > 0:
                    try:
                        decimal_value = decimal.Decimal(param_value)

                        if 'precision' in item:
                            s = str(decimal_value)
                            a = s.split(".")
                            if len(a) > 1 and len(a[1].rstrip("0")) > item['precision']:
                                errors.append(param_name + "小数点以下は" + str(item['precision']) + '桁まで指定可能です')
                                is_error = True
                            else:
                                converted_value = decimal_value

                        elif 'min_value' in item and decimal_value < decimal.Decimal(item['min_value']):
                            errors.append(param_name + " 最小値を下回っています" + str(item['min_value']))
                            is_error = True
                        elif 'max_value' in item and decimal_value > decimal.Decimal(item['max_value']):
                            errors.append(param_name + " 最大値を上回っています" + str(item['max_value']))
                            is_error = True
                        else:
                            # float型に変換も選択肢としてあるが、今はDecimalを返す
                            converted_value = decimal_value

                    except decimal.InvalidOperation:
                        errors.append(param_name + " 数値ではありません")
                        is_error = True

        # 文字列型チェック
        elif item['type'] == 'str':

            if is_required and (param_value is None or len(param_value.strip()) == 0):
                errors.append(param_name + "の指定は必須です。")
                is_error = True

            # json_bodyとそれ以外で共通
            elif not type(param_value) is str:
                errors.append(param_name + " 文字列を指定してください")
                is_error = True
            elif len(param_value.strip()) > 0:
                if 'min' in item and len(param_value) < item['min']:
                    errors.append(param_name + " 長さの下限を下回っています" + str(item['min']))
                    is_error = True
                elif 'max' in item and len(param_value) > item['max']:
                    errors.append(param_name + " 長さの上限を上回っています" + str(item['max']))
                    is_error = True

        # アップロードファイルのチェック
        elif item['type'] == 'file':

            if is_required and (param_value is None or len(param_value.strip()) == 0):
                errors.append(param_name + " ファイルがアップロードされていません")
                is_error = True

            # TODO 拡張子チェック、サイズチェック（０より大きい）、PDFファイルのメタ情報チェックなど(これはカスタムチェックぽい)
            # file = request.files['my_file']
            # ローカルに保存、システムで安全な別名を付けた方が良い
            # ローカルの保存パスをセットして返す
            # file.save('/tmp/', "tmp")
            # ファイルサイズ
            # print(os.stat(file.stream._file.name).st_size)
            pass

        else:
            raise Exception('不明なtype' + item['type'])

        if is_error:
            return

        if converted_value is not None:
            type_converted.set_value(item['src'], param_name, converted_value)
        else:
            type_converted.set_value(item['src'], param_name, param_value)


if __name__ == '__main__':

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
    # パラメータごとではなく、チェックの種類を起点にしたほうがよい？
    # いや、単項目チェックではパラメータごとか？
    # 相関チェックはチェックの種類が起点のほうがよい
    # どっちもできたほうが柔軟性が上？あまり差がないか？
    # パラメータごとの方が検証をどこでやめればよいかが明確、チェックの種類ごとだとパラメータごとのエラー状況を保持しておく必要あり

    input_request = MockRequest()

    # argsとformは値はstrでセットする
    input_request.args = {'foo': 'bar12'}
    input_request.form = {'hoge': '1.00', 'foo': 'bar12', 'key3': 'value3'
        , 'key4': '99.999', 'key9[0]': '450', 'alpha[0]': 'ccc', 'beta[0]': '100'}
    # json_bodyではいろいろなデータ型がありえる
    input_request.data = b'{"key5": 1.000, "key6": "abc", "key7": 99.999, "key8": "12345", "key10[1]": 1}'

    validator = RequestParamsValidator(spec)
    result = validator.validate(input_request)
    print("Errors")
    print(result[0])
    print("Type Converted Input params")
    print(vars(result[1]))
