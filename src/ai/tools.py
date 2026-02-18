"""Tool definitions for Claude tool_use and handler mappings."""

TOOLS = [
    {
        "name": "search_product",
        "description": (
            "Busca um produto MDF por nome, codigo, ou descricao. "
            "Use quando o vendedor mencionar um MDF especifico."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Nome, codigo ou descricao do produto MDF",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_stock",
        "description": "Verifica a disponibilidade de estoque de um produto MDF pelo seu ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID do produto para verificar estoque",
                }
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "find_direct_equivalents",
        "description": (
            "Busca equivalencias diretas (Opcao 1) para um produto. "
            "Retorna produtos de outras marcas que sao substitutos oficiais. "
            "Use quando o produto original esta sem estoque."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID do produto original",
                },
                "require_same_thickness": {
                    "type": "boolean",
                    "description": "Se true, retorna apenas equivalentes da mesma espessura",
                    "default": True,
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "find_smart_alternatives",
        "description": (
            "Busca alternativas inteligentes (Opcao 2) quando nao ha equivalente direto. "
            "Analisa atributos (categoria, padrao, acabamento, cor, espessura) e usa "
            "conhecimento especializado sobre MDFs brasileiros para sugerir os 3 produtos "
            "mais parecidos dentre os que estao EM ESTOQUE. "
            "Use quando find_direct_equivalents retornar vazio."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID do produto original sem equivalente direto",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Numero maximo de alternativas (padrao: 3)",
                    "default": 3,
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "search_web_mdf",
        "description": (
            "Pesquisa na internet por referencias sobre um produto MDF especifico. "
            "Retorna informacoes de sites especializados, fabricantes e comparativos. "
            "IMPORTANTE: Use APENAS quando o vendedor autorizar a pesquisa web explicitamente. "
            "Nunca use sem perguntar antes ao vendedor."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Nome do produto MDF para pesquisar",
                },
                "brand": {
                    "type": "string",
                    "description": "Marca do fabricante (opcional)",
                    "default": "",
                },
            },
            "required": ["product_name"],
        },
    },
    {
        "name": "find_compatible_edging_tape",
        "description": "Busca fitas de borda compativeis com um produto MDF.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID do produto MDF",
                }
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "register_feedback",
        "description": (
            "Registra feedback do vendedor sobre uma sugestao de substituicao. "
            "Use quando o vendedor indicar se aceitou ou rejeitou a sugestao."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "original_product_id": {
                    "type": "integer",
                    "description": "ID do produto original solicitado",
                },
                "suggested_product_id": {
                    "type": "integer",
                    "description": "ID do produto sugerido como substituto",
                },
                "accepted": {
                    "type": "boolean",
                    "description": "Se o vendedor aceitou a sugestao",
                },
                "rating": {
                    "type": "integer",
                    "description": "Nota de 1 a 5 (opcional)",
                },
                "comment": {
                    "type": "string",
                    "description": "Comentario do vendedor (opcional)",
                },
            },
            "required": ["original_product_id", "suggested_product_id", "accepted"],
        },
    },
    {
        "name": "generate_client_text",
        "description": (
            "Gera texto formatado pronto para enviar ao cliente via WhatsApp/email "
            "sobre a substituicao sugerida."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "original_product_id": {
                    "type": "integer",
                    "description": "ID do produto original",
                },
                "suggested_product_id": {
                    "type": "integer",
                    "description": "ID do produto substituto sugerido",
                },
                "suggestion_type": {
                    "type": "string",
                    "enum": ["direct_equivalence", "visual_similarity", "smart_alternative"],
                    "description": "Tipo da sugestao",
                },
            },
            "required": [
                "original_product_id",
                "suggested_product_id",
                "suggestion_type",
            ],
        },
    },
    {
        "name": "search_by_image",
        "description": (
            "Busca produtos MDF semelhantes a uma imagem enviada pelo vendedor. "
            "Analisa a foto enviada e compara com imagens dos produtos cadastrados no sistema. "
            "Use SEMPRE que o vendedor enviar uma foto/imagem junto com a mensagem."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Numero maximo de produtos similares para retornar",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
]
