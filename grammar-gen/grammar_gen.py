from parser import parse_file

class Predicate:
    def __init__(self, name, num_args):
        self.name = name
        self.num_args = num_args

    def __str__(self):
        if self.type_list:
            types_str = f"{', '.join([type_name.capitalize() for type_name in self.type_list])}"
        else:
            types_str = f"{', '.join(['_'] * self.num_args)}"
        return f"{self.name + '(' + types_str + ')'}"

    def set_type(self, type_list):
        assert len(type_list) == self.num_args, f'Pred: {self.name}, #Args = {self.num_args}, typeof(args): {type(self.num_args)}, type_list: {type_list}'
        self.type_list = type_list

    def set_direction(self, dir_list):
        assert len(dir_list) == self.num_args, f'Pred: {self.name}, #Args = {self.num_args}, typeof(args): {type(self.num_args)}, dir_list: {dir_list}'
        self.dir_list = dir_list

class TacticGrammar:
    max_vars = None
    max_body = None
    var_map = {'Square': ['From', 'To'], 'Pos': ['Pos']}
    pred_map = {}

    def __init__(self, bias_filename: str):
        result = parse_file(bias_filename)
        for fact in result:
            if fact.id == 'max_body':
                self.max_body = fact.args[0]
            elif fact.id == 'max_vars':
                self.max_vars = fact.args[0]
            elif fact.id == 'head_pred':
                pred_name = fact.args[0]
                pred_num_args = fact.args[1]
                predicate = Predicate(pred_name, pred_num_args)
                self.pred_map[pred_name] = predicate
                self.head_pred = pred_name
            elif fact.id == 'body_pred':
                pred_name = fact.args[0]
                pred_num_args = fact.args[1]
                predicate = Predicate(pred_name, pred_num_args)
                self.pred_map[pred_name] = predicate
            elif fact.id == 'type':
                pred_name = fact.args[0]
                type_list = fact.args[1]
                if pred_name not in self.pred_map:
                    predicate = Predicate(pred_name, len(type_list))
                    self.pred_map[fact.id] = predicate
                self.pred_map[pred_name].set_type(type_list)
            elif fact.id == 'direction':
                pred_name = fact.args[0]
                dir_list = fact.args[1]
                if pred_name not in self.pred_map:
                    predicate = Predicate(pred_name, len(dir_list))
                    self.pred_map[fact.id] = predicate
                self.pred_map[pred_name].set_direction(dir_list)

    def __str__(self):
        pred_rules_str = '\n'.join([f'{pred_name.capitalize()} -> {str(pred)}' for pred_name, pred in self.pred_map.items() if pred_name != self.head_pred])
        return f'''{self.head_pred.capitalize()} -> Predicate | ε

Predicate -> {' | '.join([pred_name.capitalize() for pred_name in self.pred_map.keys() if pred_name != self.head_pred])}

{pred_rules_str}'''

if __name__ == '__main__':  
    filename = 'bias.pl'
    grammar = TacticGrammar(filename)
    print(grammar)