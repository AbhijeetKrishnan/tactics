# Source: https://stackoverflow.com/a/24490005

import pyparsing as pp

def create_parser():
    predicate = pp.Word(pp.alphas + '_').set_results_name('id')

    number = pp.Word(pp.nums + '.').set_parse_action(lambda s, l, t: [int(t[0])])
    variable = pp.Word(pp.alphas + '_')

    # an argument to a fact can be either a number or a variable
    simple_arg = number | variable

    # arguments are a delimited list of 'argument' surrounded by parenthesis
    simple_arg_list = pp.Group(pp.Suppress('(') + pp.delimited_list(simple_arg, delim=',') +
                               pp.Suppress(')'))
    
    arg = simple_arg | simple_arg_list

    arguments = (pp.Suppress('(') + pp.delimited_list(arg, delim=',') + 
                 pp.Suppress(')')).set_results_name('args')

    fact = (predicate + arguments)

    # a sentence is a fact plus a period
    sentence = (fact + pp.Suppress('.'))

    comment = pp.Literal('%') + pp.Word(pp.alphanums + '_' + ' ' + ',')

    prolog_parser = pp.OneOrMore(pp.Group(sentence)).ignore(comment)
    return prolog_parser

prolog = create_parser()

def parse_file(filename):
    result = prolog.parse_file(filename, parse_all=True)
    return result

def to_pred_str(predicate):
    return f'{predicate.id}/{len(predicate.args)}'

def to_pred(predicate):
    return f'{predicate.id}({",".join(predicate.args)})'

def get_pred_str_list(results):
    return [to_pred_str(predicate) for predicate in results]

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

    result = parse_file('examples/even/pos.pl')
    print(result.dump())