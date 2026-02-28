# 🚀 Checklist de Validação Antes de Implementar Novas Features

Use este checklist para garantir que cada nova feature está bem testada antes de adicionar mais código.

## ✅ Pré-Implementação

Antes de começar:
- [ ] Feature está claramente definida
- [ ] Dependências externas são mínimas
- [ ] Mockable/testável

## 🧪 Durante Implementação

1. **Testes Unitários**
   - [ ] Testar caso de sucesso (happy path)
   - [ ] Testar caso vazio/sem dados
   - [ ] Testar erro/exceção
   - [ ] Testar edge cases

2. **Testes de Integração**
   - [ ] Testar com banco de dados real (em memória)
   - [ ] Testar fluxo completo
   - [ ] Testar com múltiplos dados

3. **Cobertura de Código**
   - [ ] Rodar: `pytest --cov=ai --cov=memory --cov-report=term-missing`
   - [ ] Cobertura >= 80%
   - [ ] Sem linhas não cobertas em código crítico

## ✨ Validação Final

Antes de commitar:

```bash
# 1. Rodar todos os testes
pytest -v

# 2. Verificar cobertura
pytest --cov=ai --cov=memory --cov-report=term-missing

# 3. Verificar linting (opcional, mas recomendado)
pylint ai/*.py

# 4. Verificar type hints (opcional)
mypy ai/*.py --ignore-missing-imports

# 5. Testar na CLI manualmente (smoke test)
python main.py
> Sua mensagem para testar feature
```

## 📋 Template de Teste para Nova Feature

```python
import pytest

class TestNovaFeature:
    
    def test_caso_sucesso(self, fixtures_necessarios):
        """Testa happy path"""
        # ARRANGE
        dados = prepare_dados()
        
        # ACT
        resultado = nova_funcao(dados)
        
        # ASSERT
        assert resultado is not None
        assert resultado.propriedade == esperado
    
    def test_caso_vazio(self, fixtures_necessarios):
        """Testa sem dados"""
        resultado = nova_funcao(dados_vazios=[])
        assert resultado.total == 0
    
    def test_caso_erro(self, fixtures_necessarios):
        """Testa tratamento de erro"""
        with pytest.raises(ExpectedException):
            nova_funcao(dados_invalidos)
```

## 🔄 Workflow de Implementação

1. **Escrever testes primeiro (TDD)**
   ```bash
   # Teste vai falhar inicialmente
   pytest tests/test_nova_feature.py -v
   ```

2. **Implementar código**
   ```python
   # Escrive a lógica que passa nos testes
   ```

3. **Verificar testes passam**
   ```bash
   pytest tests/test_nova_feature.py -v
   # Deve dar: PASSED
   ```

4. **Adicionar testes de integração**
   ```python
   # Testa com dados reais
   ```

5. **Verificar cobertura**
   ```bash
   pytest --cov=ai --cov=memory --cov-report=html
   # Abrir htmlcov/index.html
   ```

6. **Revisar código**
   - [ ] Sem comentários desnecessários
   - [ ] Nomes de variáveis claros
   - [ ] Type hints presente
   - [ ] Docstrings quando necessário

7. **Smoke test**
   ```bash
   python main.py
   # Testar manualmente a feature na CLI
   ```

## 📊 Métricas de Qualidade

| Métrica | Alvo | Método |
|---------|------|--------|
| Code Coverage | ≥80% | `pytest --cov --cov-report=term-missing` |
| Tests Passed | 100% | `pytest` |
| Type Checking | Clean | `mypy .` |
| Linting | 0 errors | `pylint ai/` |

## 🛠️ Troubleshooting

### Teste falha com "No module found"
```bash
# Certifique-se que conftest.py está em tests/
# E que sys.path está configurado corretamente
```

### Mock não está funcionando
```python
# Use @patch decorator corretamente
from unittest.mock import patch

@patch('caminho.completo.para.modulo')
def test_exemplo(self, mock_objeto):
    mock_objeto.return_value = valor_esperado
```

### Cobertura baixa
```bash
# Veja qual código não está coberto
pytest --cov=ai --cov-report=term-missing

# Adicione testes para:
# - Linhas faltantes
# - Branches (if/else)
# - Exceções
```

## ✅ Exemplo: Checklist Preenchido para ANALYZE

- [x] Feature está claramente definida (análise do perfil)
- [x] Testado caso de sucesso (com 10 tracks)
- [x] Testado caso vazio (sem tracks)
- [x] Testado com scores de diversidade
- [x] Cobertura >= 85%
- [x] Rodar pytest -v ✅ PASSED
- [x] Smoke test na CLI ✅ Funciona
- [x] Sem comentários desnecessários
- [x] Type hints presentes

---

**Status:** ✅ Pronto para próxima feature!
