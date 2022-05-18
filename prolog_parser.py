# Source: https://stackoverflow.com/a/24490005

import pyparsing as pp

# TODO: brainstorm how to add this info in the bias file
PRED_VALUE = {
    'make_move': 0,
    'legal_move': 0,
    'attacks': 1,
    'behind': 1,
    'piece_at': 2,
    'different_pos': 3,
    'other_side': 3
}

def create_parser():
    predicate = pp.Word(pp.alphas + '_').set_results_name('id')

    number = pp.Word(pp.nums + '.').set_parse_action(lambda s, l, t: [int(t[0])])
    variable = pp.Word(pp.alphas + pp.nums + '_')

    # an argument to a fact can be either a number or a variable
    simple_arg = number | variable

    # arguments are a delimited list of 'argument' surrounded by parenthesis
    simple_arg_list = pp.Group(pp.Suppress('(') + pp.delimited_list(simple_arg, delim=',') +
                               pp.Suppress(')'))
    
    arg = simple_arg | simple_arg_list

    arguments = (pp.Suppress('(') + pp.delimited_list(arg, delim=',') + 
                 pp.Suppress(')')).set_results_name('args')

    fact = (predicate + arguments)

    comment = pp.Literal('%') + pp.Word(pp.alphanums + '_' + ' ' + ',' + ':')

    rule = (pp.Group(fact) + pp.Suppress(pp.Literal(':-')) + pp.delimited_list(pp.Group(fact), delim=',') + pp.Suppress('.'))

    prolog_parser = pp.OneOrMore(pp.Group(rule)).ignore(comment)
    return rule

def to_pred_str(predicate) -> str:
    return f'{predicate.id}/{len(predicate.args)}'

def to_pred(predicate) -> str:
    "Converts a parsed predicate into its string representation"

    return f'{predicate.id}({",".join(predicate.args)})'

def get_pred_str_list(results):
    return [to_pred_str(predicate) for predicate in results]

def parse_result_to_str(parse_result) -> str:
    "Converts a parsed hypothesis space into a list of tactics represented by strings"

    head_pred_str = to_pred(parse_result[0])
    body_preds = parse_result[1:]
    body_preds.sort(key=lambda pred: PRED_VALUE[pred.id])
    body_preds_str = ','.join([to_pred(pred) for pred in body_preds])
    tactic_str = f'{head_pred_str}:-{body_preds_str}'
    return tactic_str

def get_all_unique_args(results):
    res = []
    for predicate in results:
        res.extend(predicate.args)
    return list(set(res))

if __name__ == '__main__':
    prolog_sentences = create_parser()

    test="""track(1, 2.0, 4000, 3, 300).
    track(2, 1.0, 9000, 5, 500).
    track(3, 7.0, 9000, 2, 200)."""

    result = prolog_sentences.parse_string(test, parse_all=True)

    print(result[0].args)
    # outputs ['1', '2.0', '4000', '3', '300']

    print(result[1].id)
    # outputs 'track'

    print(result[2].args[1])
    # outputs ['7.0']

    result = prolog_sentences.parse_file('examples/even/pos.pl')
    print(result.dump())