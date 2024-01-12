# String original
valor_str = "110454"

# Dividir em parte inteira e parte decimal
parte_inteira = valor_str[:-2]
parte_decimal = valor_str[-2:]

# Combinação para obter o valor float
valor_float = float(f"{parte_inteira}.{parte_decimal}")

# Imprimir o resultado
print(valor_float)
