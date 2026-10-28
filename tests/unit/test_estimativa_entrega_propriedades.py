"""Propriedades da estimativa de entrega (RF-25), para qualquer combinação de serviços e peças.

Os sorteios usam semente fixa, para o teste ser reproduzível. Cada propriedade compara duas OS
que diferem em um único item, em vez de repetir a conta do método.
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from domain.entities.ordem_servico import OrdemServico
from domain.entities.peca import Peca
from domain.entities.servico import Servico
from domain.value_objects.numero_os import NumeroOS
from domain.value_objects.status_os import StatusOS
from domain.value_objects.valor import Valor

SEMENTE = 20261029
SORTEIOS = 2000
BASE = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)

AGUARDANDO = [
    StatusOS.AGUARDANDO_APROVACAO,
    StatusOS.AGUARDANDO_PECA,
    StatusOS.AGUARDANDO_EXECUCAO,
]
SEM_ESTIMATIVA = [StatusOS.RECEBIDA, StatusOS.EM_DIAGNOSTICO, StatusOS.CANCELADA]
COM_PRAZO_DAS_PECAS = [StatusOS.AGUARDANDO_APROVACAO, StatusOS.AGUARDANDO_PECA]
COM_DURACAO = [*AGUARDANDO, StatusOS.EM_EXECUCAO]
JA_REGISTRADOS = [StatusOS.EM_EXECUCAO, StatusOS.FINALIZADA, StatusOS.ENTREGUE]


def _os(status, minutos, pecas) -> OrdemServico:
    """OS no status pedido, com serviços de `minutos` e peças de (prazo, pendente), 2 unidades."""
    os = OrdemServico(
        numero=NumeroOS("529-7F3A9C2B"),
        cliente_id=uuid4(),
        veiculo_id=uuid4(),
        atendente_id=uuid4(),
        status=StatusOS.EM_DIAGNOSTICO,
    )
    for tempo in minutos:
        os.incluir_servico(
            Servico(
                codigo=str(uuid4()),
                nome="Serviço",
                descricao="Descrição",
                valor_base=Valor("1"),
                tempo_estimado_minutos=tempo,
            )
        )
    for prazo, pendente in pecas:
        os.incluir_peca(
            Peca(
                codigo_referencia=str(uuid4()),
                nome="Peça",
                preco_unitario=Valor("1"),
                prazo_reposicao_dias=prazo,
            ),
            quantidade=2,
        )
        os.pecas[-1].quantidade_pendente = pendente
        os.pecas[-1].quantidade_reservada = 2 - pendente
    os.status = status
    os.data_inicio_execucao = BASE + timedelta(hours=1)
    os.data_finalizacao = BASE + timedelta(hours=9)
    return os


def _itens_sorteados(sorteio: random.Random):
    minutos = [sorteio.randint(0, 600) for _ in range(sorteio.randint(0, 4))]
    pecas = [(sorteio.randint(0, 30), sorteio.randint(0, 2)) for _ in range(sorteio.randint(0, 4))]
    return minutos, pecas


def _prazo_maximo_pendente(pecas) -> int:
    return max((prazo for prazo, pendente in pecas if pendente > 0), default=0)


def test_as_propriedades_da_estimativa_valem_para_qualquer_combinacao_de_itens():
    sorteio = random.Random(SEMENTE)

    for _ in range(SORTEIOS):
        status = sorteio.choice(list(StatusOS))
        minutos, pecas = _itens_sorteados(sorteio)
        consulta = BASE + timedelta(minutes=sorteio.randint(0, 100_000))
        os = _os(status, minutos, pecas)
        estimativa = os.estimar_entrega(consulta)

        if status in SEM_ESTIMATIVA:
            assert estimativa is None
            continue
        assert estimativa is not None

        if status in AGUARDANDO:
            assert estimativa >= consulta

        if status in JA_REGISTRADOS:
            outra_consulta = consulta + timedelta(days=sorteio.randint(1, 400))
            assert os.estimar_entrega(outra_consulta) == estimativa

        if status in (StatusOS.FINALIZADA, StatusOS.ENTREGUE):
            assert estimativa == os.data_finalizacao
            assert _os(status, minutos + [999], pecas).estimar_entrega(consulta) == estimativa

        # Um serviço a mais de N minutos adia a estimativa em exatamente N minutos.
        if status in COM_DURACAO:
            extra = sorteio.randint(0, 600)
            com_servico = _os(status, minutos + [extra], pecas).estimar_entrega(consulta)
            assert com_servico - estimativa == timedelta(minutes=extra)

        # Uma peça pendente a mais só adia a estimativa se o prazo dela for o maior, e só até ele.
        if status in COM_PRAZO_DAS_PECAS:
            prazo = sorteio.randint(0, 40)
            com_peca = _os(status, minutos, [*pecas, (prazo, 1)]).estimar_entrega(consulta)
            folga = max(0, prazo - _prazo_maximo_pendente(pecas))
            assert com_peca - estimativa == timedelta(days=folga)

        # Peça já reservada nunca muda a estimativa, e nenhuma peça muda a das demais fases.
        for prazo in (0, 17, 400):
            com_reservada = _os(status, minutos, [*pecas, (prazo, 0)]).estimar_entrega(consulta)
            assert com_reservada == estimativa
        if status not in COM_PRAZO_DAS_PECAS:
            com_peca = _os(status, minutos, [*pecas, (30, 1)]).estimar_entrega(consulta)
            assert com_peca == estimativa
