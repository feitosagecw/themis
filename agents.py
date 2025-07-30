from typing import Callable, List, Any

def function_tool(func: Callable) -> Callable:
    """Decorador para marcar funções como ferramentas de agente."""
    func.is_tool = True
    return func

class Agent:
    def __init__(self, name: str, instructions: str, model: str, tools: List[Callable]):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.tools = tools

    def run(self, **kwargs) -> Any:
        # Busca a função correta pelo nome do primeiro argumento
        if not self.tools:
            raise Exception("Nenhuma ferramenta registrada para este agente.")
        # Usa a primeira ferramenta (função) da lista
        tool = self.tools[0]
        return tool(**kwargs) 