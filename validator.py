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


def validate(spec, input_request):
    errors = []

    # src == json_bodyがある場合
    is_json_body = False
    is_json_body_required = False
    for item in spec:
        if is_json_body_required:
            break
        if item['src'] == 'json_body':
            is_json_body = True
            for t in item['types']:
                if t['type'] == 'required':
                    is_json_body_required = True
                    break

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

    for item in spec:

        # 添え字付きのパラメータの場合
        if 'indexed' in item and item['indexed']:

            param_name = item['param_name']

            # 必須か
            validation_types = item['types']

            is_required = False
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

            validate_param(param_name, param_value, item, type_converted, errors)

    # 添え字番号でソート
    sorted(indexed_params, key=lambda x: x[0])
    print("paramsソート後", indexed_params)
    for param in indexed_params:
        validate_param(param[1], param[2], param[3], type_converted, errors)

    return errors, type_converted


# １つのパラメータの検証
def validate_param(param_name, param_value, item, type_converted, errors):

    validation_types = item['types']

    is_required = False
    for t in validation_types:
        if t['type'] == 'required':
            is_required = True
            break

    # 必須ではない項目は値が指定されていなければ検証しなくてよい
    if not is_required and (param_value is None or len(str(param_value).strip()) == 0):
        # 次の項目へ
        return

    converted_value = None
    is_error = False

    for t in validation_types:

        # 必須チェック
        if t['type'] == 'required':

            if param_value is None or len(str(param_value).strip()) == 0:
                errors.append(param_name + "の指定は必須です。")
                is_error = True
                # 次の項目へ
                break

        # 整数チェック
        elif t['type'] == 'integer':

            if item['src'] == 'json_body':
                if type(param_value) is int:
                    pass
                elif type(param_value) is float:
                    if not param_value.is_integer():
                        errors.append(param_name + ' 整数を指定してください')
                        is_error = True
                        break
                elif type(param_value) is str:
                    if 'convert_str' in t and t['convert_str']:
                        try:
                            decimal_value = decimal.Decimal(param_value)
                            if not (decimal_value % 1 == 0):
                                errors.append(param_name + ' 整数を指定してください')
                                is_error = True
                                break
                            converted_value = int(decimal_value)
                        except decimal.InvalidOperation:
                            errors.append(param_name + " 数値ではありません")
                            is_error = True
                            break
                    else:
                        errors.append(param_name + " 値が数値型ではありません")
                        is_error = True
                        break
                else:
                    errors.append(param_name + " 値が数値型ではありません")
                    is_error = True
                    break
            else:
                # json_body以外

                if type(param_value) is float and not param_value.is_integer():
                    errors.append(param_name + " 整数ではありません")
                    is_error = True
                    break

                try:
                    converted_value = int(param_value)
                    if 'min_value' in t and converted_value < t['min_value']:
                        errors.append(param_name + " 最小値を下回っています" + str(t['min_value']))
                        is_error = True
                        break
                    if 'max_value' in t and converted_value > t['max_value']:
                        errors.append(param_name + " 最大値を上回っています" + str(t['max_value']))
                        is_error = True
                        break

                except ValueError:
                    errors.append(param_name + " の値が整数ではありません")
                    is_error = True
                    break

        # 小数点あり数値
        elif t['type'] == 'float':
            if item['src'] == 'json_body':
                if type(param_value) is float:
                    converted_value = decimal.Decimal(str(param_value))
                elif type(param_value) is int:
                    converted_value = decimal.Decimal(param_value)
                elif type(param_value) is str:
                    if 'convert_str' in t and t['convert_str']:
                        try:
                            decimal_value = decimal.Decimal(param_value)

                            if 'precision' in t:
                                s = str(decimal_value)
                                a = s.split(".")
                                if len(a) > 1 and len(a[1].rstrip("0")) > t['precision']:
                                    errors.append(param_name + "小数点以下は" + str(t['precision']) + 'までです')
                                    is_error = True
                                    break

                            if 'min_value' in t and decimal_value < decimal.Decimal(t['min_value']):
                                errors.append(param_name + " 最小値を下回っています" + str(t['min_value']))
                                is_error = True
                                break
                            if 'max_value' in t and decimal_value > decimal.Decimal(t['max_value']):
                                errors.append(param_name + " 最大値を上回っています" + str(t['max_value']))
                                is_error = True
                                break

                            # float型に変換も選択肢としてあるが、今はDecimalを返す
                            converted_value = decimal_value

                        except decimal.InvalidOperation:
                            errors.append(param_name + " 数値ではありません")
                            is_error = True
                            break
                    else:
                        errors.append(param_name + " 値が数値型ではありません")
                        is_error = True
                        break
                else:
                    errors.append(param_name + " 値が数値型ではありません")
                    is_error = True
                    break

            else:
                # json_body以外
                try:
                    decimal_value = decimal.Decimal(str(param_value))

                    if 'precision' in t:
                        s = str(decimal_value)
                        print("s", s)
                        a = s.split(".")
                        if len(a) > 1 and len(a[1].rstrip("0")) > t['precision']:
                            errors.append(param_name + "小数点以下は" + str(t['precision']) + 'までです')
                            is_error = True
                            break

                    if 'min_value' in t and decimal_value < decimal.Decimal(t['min_value']):
                        errors.append(param_name + " 最小値を下回っています" + str(t['min_value']))
                        is_error = True
                        break
                    if 'max_value' in t and decimal_value > decimal.Decimal(t['max_value']):
                        errors.append(param_name + " 最大値を上回っています" + str(t['max_value']))
                        is_error = True
                        break

                    # float型に変換も選択肢としてあるが、今はDecimalを返す
                    converted_value = decimal_value

                except decimal.InvalidOperation:
                    errors.append(param_name + " 数値ではありません")
                    is_error = True
                    break

        # 文字列型チェック
        elif t['type'] == 'str':

            # json_bodyとそれ以外で共通
            if not type(param_value) is str:
                errors.append(param_name + " 文字列を指定してください")
                is_error = True
                break

            if 'min' in t and len(param_value) < t['min']:
                errors.append(param_name + " 長さの下限を下回っています" + str(t['min']))
                is_error = True
                break
            if 'max' in t and len(param_value) > t['max']:
                errors.append(param_name + " 長さの上限を上回っています" + str(t['max']))
                is_error = True
                break
        else:
            raise Exception('不明なtype' + t['type'])

    if is_error:
        return

    if converted_value is not None:
        type_converted.set_value(item['src'], param_name, converted_value)
    else:
        type_converted.set_value(item['src'], param_name, param_value)


if __name__ == '__main__':
    spec = [{'param_name': 'hoge', 'src': 'form'
                , 'types': [
            {'type': 'required'},
            {'type': 'integer', 'min_value': 0, 'max_value': 500}
        ]}, {'param_name': 'foo', 'src': 'query'
                , 'types': [
            {'type': 'required'},
            {'type': 'str', 'max': 5, 'min': 5}
        ]}, {'param_name': 'key4', 'src': 'form'
                , 'types': [
            {'type': 'required'},
            {'type': 'float', 'precision': 3, 'min_value': "0.001", 'max_value': '99.999'}
        ]}, {'param_name': 'key5', 'src': 'json_body'
                , 'types': [
            {'type': 'required'},
            {'type': 'integer', 'min_value': 0, 'max_value': 500}
        ]}, {'param_name': 'key6', 'src': 'json_body'
                , 'types': [
            {'type': 'required'}
        ]}, {'param_name': 'key7', 'src': 'json_body'
                , 'types': [
            {'type': 'required'},
            {'type': 'float', 'precision': 3, 'min_value': "0.001", 'max_value': '99.999', 'convert_str': True}
        ]}, {'param_name': 'key8', 'src': 'json_body'
                , 'types': [
            {'type': 'str', 'max': 5, 'min': 5}
        ]}, {'param_name': 'key9', 'src': 'form', 'indexed': True
                , 'types': [
            {'type': 'required'},
            {'type': 'integer', 'min_value': 0, 'max_value': 500}
        ]}, {'param_name': 'key10', 'src': 'json_body', 'indexed': True
                , 'types': [
            {'type': 'required'},
            {'type': 'float', 'min_value': "0.001", 'max_value': "100"}
        ]}
            ]

    input_request = MockRequest()

    input_request.args = {'foo': 'bar12'}
    input_request.form = {'hoge': 1.00, 'foo': 'bar12', 'key3': 'value3'
        , 'key4': '99.999', 'key9[0]': 450}
    input_request.data = b'{"key5": 1.000, "key6": "abc", "key7": 99.999, "key8": "12345", "key10[1]": 1}'

    result = validate(spec, input_request)
    print("Errors")
    print(result[0])
    print("Type Converted Input params")
    print(vars(result[1]))
