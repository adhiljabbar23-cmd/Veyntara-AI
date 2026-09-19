def calculate_financials(price,variable_cost,fixed_cost):
    
    contribution_per_unit = price - variable_cost
    
    if contribution_per_unit <= 0:
        return{
            "contribution_per_unit" : contribution_per_unit,
            "break_even_units" : None,
            "message" : "The business loses money on every unit." 
        }
        
    break_even_units = fixed_cost / contribution_per_unit 
    
    return {
        "price" : price,
        "variable_cost" : variable_cost,
        "fixed_cost" : fixed_cost,
         "contribution_per_unit" : contribution_per_unit,
         "break_even_units" : round(break_even_units)
    }