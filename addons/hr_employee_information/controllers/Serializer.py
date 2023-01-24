
def format_json(data:list)->list:
    result = []
    for item in data:
        __tempo = {}
        for i in item.keys():
            if isinstance(item[i],tuple):
                __tempo[i]=format_json_many2one(data=item[i])
                pass
            else:
                __tempo[i]=item[i]
        result.append(__tempo)
    return result


def format_json_many2one(data:tuple)->dict:
    if isinstance(data,tuple):
        return {'id':data[0],'name':data[1]}
    else:
        return f"this field isn't Many2one Field."
