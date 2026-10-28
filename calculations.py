
import math


def calculate_required_units(required_contribution, price, variable_cost):
    if required_contribution < 0:
        raise ValueError("Required contribution cannot be negative.")

    if price < 0 or variable_cost < 0:
        raise ValueError("Price and variable cost cannot be negative.")

    contribution_per_unit = price - variable_cost

    if contribution_per_unit <= 0:
        return None

    required_units = math.ceil(
        required_contribution / contribution_per_unit
    )

    return {
        "contribution_per_unit": contribution_per_unit,
        "required_units": required_units
    }


def calculate_financials(price, variable_cost, fixed_cost):
    if price < 0:
        raise ValueError("Selling price cannot be negative.")

    if variable_cost < 0:
        raise ValueError("Variable cost cannot be negative.")

    if fixed_cost < 0:
        raise ValueError("Fixed cost cannot be negative.")

    contribution_per_unit = price - variable_cost

    if contribution_per_unit <= 0:
        return {
            "error": (
                "Selling price must be greater than variable cost."
            )
        }

    break_even_units = math.ceil(
        fixed_cost / contribution_per_unit
    )

    return {
        "contribution_per_unit": contribution_per_unit,
        "break_even_units": break_even_units
    }
