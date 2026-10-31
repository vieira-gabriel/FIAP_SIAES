from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from application.ports.token_service import UsuarioAutenticado
from application.use_cases.atribuir_mecanico import AtribuirMecanico
from application.use_cases.criar_os import (
    CriarOS,
    DadosDoNovoCliente,
    DadosDoNovoVeiculo,
)
from application.use_cases.detalhar_ordem_servico import DetalharOrdemServico
from application.use_cases.finalizar_orcamento import FinalizarOrcamento
from application.use_cases.incluir_peca_na_os import IncluirPecaNaOS
from application.use_cases.incluir_servico_na_os import IncluirServicoNaOS
from application.use_cases.listar_ordens_servico import CriteriosDaListagem, ListarOrdensServico
from application.use_cases.remover_peca_da_os import RemoverPecaDaOS
from application.use_cases.remover_servico_da_os import RemoverServicoDaOS
from domain.value_objects.documento import Documento
from domain.value_objects.perfil_usuario import PerfilUsuario
from domain.value_objects.placa import Placa
from domain.value_objects.status_os import StatusOS
from presentation.container import (
    obter_atribuir_mecanico,
    obter_criar_os,
    obter_detalhar_ordem_servico,
    obter_finalizar_orcamento,
    obter_incluir_peca_na_os,
    obter_incluir_servico_na_os,
    obter_listar_ordens_servico,
    obter_remover_peca_da_os,
    obter_remover_servico_da_os,
)
from presentation.middlewares.dependencies import exigir_perfis
from presentation.schemas.erro import ErroResponse
from presentation.schemas.ordem_servico import (
    AbrirOSRequest,
    AtribuirMecanicoRequest,
    IncluirPecaRequest,
    IncluirServicoRequest,
    OSDetalheResponse,
    OSItensResponse,
    OSResponse,
    OSResumoResponse,
)

router = APIRouter(
    prefix="/ordens-servico",
    tags=["Ordens de serviço"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErroResponse, "description": "Token ausente."},
        status.HTTP_403_FORBIDDEN: {"model": ErroResponse, "description": "Perfil sem permissão."},
    },
)

# RF-13: a abertura é do Atendente e do Gerente.
_ABERTURA = exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.GERENTE)
# RF-16: a atribuição do mecânico é do Mecânico e do Gerente.
_ATRIBUICAO = exigir_perfis(PerfilUsuario.MECANICO, PerfilUsuario.GERENTE)
# RF-17: os itens e a conclusão do orçamento são do Mecânico e do Gerente.
_DIAGNOSTICO = exigir_perfis(PerfilUsuario.MECANICO, PerfilUsuario.GERENTE)
# RF-14, RF-15: a consulta é de todos os perfis.
_CONSULTA = exigir_perfis(PerfilUsuario.ATENDENTE, PerfilUsuario.MECANICO, PerfilUsuario.GERENTE)

_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErroResponse,
        "description": "Cliente ou veículo não cadastrado e sem os dados para cadastrá-lo.",
    }
}
_ITEM_NAO_ENCONTRADO = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErroResponse,
        "description": "OS, serviço, peça ou item da OS não encontrado.",
    }
}
_ITEM_RECUSADO = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": (
            "OS fora de `EM_DIAGNOSTICO`, serviço ou peça excluído, item repetido ou "
            "dados fora do formato."
        ),
    }
}
_REGRA_VIOLADA = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErroResponse,
        "description": "Placa de outro cliente, documento já cadastrado ou dados fora do formato.",
    }
}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=_NAO_ENCONTRADO | _REGRA_VIOLADA,
)
async def abrir_os(
    dados: AbrirOSRequest,
    usuario: Annotated[UsuarioAutenticado, Depends(_ABERTURA)],
    abrir: Annotated[CriarOS, Depends(obter_criar_os, scope="function")],
) -> OSResponse:
    """Abre a OS em `RECEBIDA`. Cliente e veículo que não existem são cadastrados se os dados
    forem informados no corpo (RF-04, RF-07, RF-13)."""
    os = await abrir.executar(
        Documento.de_texto(dados.documento),
        Placa(dados.placa),
        usuario.usuario_id,
        cliente_novo=(
            DadosDoNovoCliente(dados.cliente.nome, dados.cliente.email, dados.cliente.telefone)
            if dados.cliente
            else None
        ),
        veiculo_novo=(
            DadosDoNovoVeiculo(dados.veiculo.marca, dados.veiculo.modelo, dados.veiculo.ano)
            if dados.veiculo
            else None
        ),
    )
    return OSResponse.de_entidade(os)


@router.get("")
async def listar_os(
    _usuario: Annotated[UsuarioAutenticado, Depends(_CONSULTA)],
    listar: Annotated[ListarOrdensServico, Depends(obter_listar_ordens_servico)],
    documento: str | None = None,
    placa: str | None = None,
    status: StatusOS | None = None,
    mecanico_id: UUID | None = None,
    abertura_de: datetime | None = None,
    abertura_ate: datetime | None = None,
) -> list[OSResumoResponse]:
    """As OS que atendem a todos os filtros informados, das mais recentes às mais antigas
    (RF-14). Sem filtros, lista todas."""
    resumos = await listar.executar(
        CriteriosDaListagem(
            documento=Documento.de_texto(documento) if documento else None,
            placa=Placa(placa) if placa else None,
            status=status,
            mecanico_id=mecanico_id,
            abertura_de=abertura_de,
            abertura_ate=abertura_ate,
        )
    )
    return [OSResumoResponse.de_resumo(resumo) for resumo in resumos]


@router.get(
    "/{id}",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErroResponse, "description": "OS não encontrada."}
    },
)
async def detalhar_os(
    id: UUID,
    _usuario: Annotated[UsuarioAutenticado, Depends(_CONSULTA)],
    detalhar: Annotated[DetalharOrdemServico, Depends(obter_detalhar_ordem_servico)],
) -> OSDetalheResponse:
    """Todos os dados da OS, com itens, quantidades reservadas e pendentes, histórico e a
    estimativa de entrega do momento da consulta (RF-15, RF-25)."""
    detalhe = await detalhar.executar(id, datetime.now(UTC))
    return OSDetalheResponse.de_detalhe(detalhe)


@router.post(
    "/{id}/mecanico",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErroResponse,
            "description": "OS ou mecânico não encontrado.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErroResponse,
            "description": "OS fora de `RECEBIDA` ou usuário que não é um mecânico ativo.",
        },
    },
)
async def atribuir_mecanico(
    id: UUID,
    usuario: Annotated[UsuarioAutenticado, Depends(_ATRIBUICAO)],
    atribuir: Annotated[AtribuirMecanico, Depends(obter_atribuir_mecanico, scope="function")],
    dados: AtribuirMecanicoRequest | None = None,
) -> OSResponse:
    """O Mecânico assume a OS, e o Gerente a atribui ao mecânico informado em `mecanico_id`. A OS
    passa de `RECEBIDA` para `EM_DIAGNOSTICO` (RF-16)."""
    mecanico_id = dados.mecanico_id if dados else None
    if mecanico_id is None and usuario.perfil == PerfilUsuario.MECANICO:
        mecanico_id = usuario.usuario_id
    os = await atribuir.executar(id, mecanico_id, usuario.usuario_id)
    return OSResponse.de_entidade(os)


@router.post(
    "/{id}/servicos",
    status_code=status.HTTP_201_CREATED,
    responses=_ITEM_NAO_ENCONTRADO | _ITEM_RECUSADO,
)
async def incluir_servico(
    id: UUID,
    dados: IncluirServicoRequest,
    _usuario: Annotated[UsuarioAutenticado, Depends(_DIAGNOSTICO)],
    incluir: Annotated[IncluirServicoNaOS, Depends(obter_incluir_servico_na_os, scope="function")],
) -> OSItensResponse:
    """Inclui um serviço ativo do catálogo na OS, que precisa estar em `EM_DIAGNOSTICO` (RF-17)."""
    return OSItensResponse.de_entidade(await incluir.executar(id, dados.servico_id))


@router.delete(
    "/{id}/servicos/{servico_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ITEM_NAO_ENCONTRADO | _ITEM_RECUSADO,
)
async def remover_servico(
    id: UUID,
    servico_id: UUID,
    _usuario: Annotated[UsuarioAutenticado, Depends(_DIAGNOSTICO)],
    remover: Annotated[RemoverServicoDaOS, Depends(obter_remover_servico_da_os, scope="function")],
) -> None:
    """Tira o serviço da OS, que precisa estar em `EM_DIAGNOSTICO` (RF-17)."""
    await remover.executar(id, servico_id)


@router.post(
    "/{id}/pecas",
    status_code=status.HTTP_201_CREATED,
    responses=_ITEM_NAO_ENCONTRADO | _ITEM_RECUSADO,
)
async def incluir_peca(
    id: UUID,
    dados: IncluirPecaRequest,
    _usuario: Annotated[UsuarioAutenticado, Depends(_DIAGNOSTICO)],
    incluir: Annotated[IncluirPecaNaOS, Depends(obter_incluir_peca_na_os, scope="function")],
) -> OSItensResponse:
    """Inclui uma peça ativa do catálogo na OS, com a quantidade, que precisa estar em
    `EM_DIAGNOSTICO`. A reserva no estoque só acontece na conclusão do orçamento (RF-17, RF-18)."""
    return OSItensResponse.de_entidade(await incluir.executar(id, dados.peca_id, dados.quantidade))


@router.delete(
    "/{id}/pecas/{peca_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ITEM_NAO_ENCONTRADO | _ITEM_RECUSADO,
)
async def remover_peca(
    id: UUID,
    peca_id: UUID,
    _usuario: Annotated[UsuarioAutenticado, Depends(_DIAGNOSTICO)],
    remover: Annotated[RemoverPecaDaOS, Depends(obter_remover_peca_da_os, scope="function")],
) -> None:
    """Tira a peça da OS, que precisa estar em `EM_DIAGNOSTICO` (RF-17)."""
    await remover.executar(id, peca_id)


@router.post(
    "/{id}/orcamento",
    responses=_ITEM_NAO_ENCONTRADO | _ITEM_RECUSADO,
)
async def concluir_orcamento(
    id: UUID,
    usuario: Annotated[UsuarioAutenticado, Depends(_DIAGNOSTICO)],
    finalizar: Annotated[FinalizarOrcamento, Depends(obter_finalizar_orcamento, scope="function")],
) -> OSItensResponse:
    """Congela os valores vigentes do catálogo e envia o orçamento ao cliente: a OS passa de
    `EM_DIAGNOSTICO` para `AGUARDANDO_APROVACAO` (RF-17)."""
    return OSItensResponse.de_entidade(await finalizar.executar(id, usuario.usuario_id))
