"""Dados fictícios completos (chaves = as do layout atual) para testes e demonstração."""
ESTAB = {"cnes": "2733579", "nome_fantasia": "HOSPITAL REGIONAL EXEMPLO"}
FICHA20 = dict(
    cadastramento="SUS", nome="MARIA APARECIDA DA SILVA SANTOS OLIVEIRA", pis="12345678919",
    cpf="52998224725", cns="700000000000005", sexo="F", mae="JOANA PEREIRA DA SILVA",
    pai="JOSE CARLOS DA SILVA", data_nasc="05/03/1985", mun_nasc="ASTORGA", ibge_nasc="410190",
    uf_nasc="PR", raca_cor="01", cert_tipo="1", cartorio="CARTORIO DE REGISTRO CIVIL DE ASTORGA",
    livro="A123", fls="045", termo="12345", cert_data="10/04/1985", rg_num="123456789",
    rg_uf="PR", rg_orgao="SESP", rg_data="15/06/2003", nacionalidade="B", pais_origem="010",
    data_entrada="01/02/2020", data_naturalizacao="", portaria="", titulo="123456789012",
    zona="123", secao="0456", ctps_num="1234567", ctps_serie="00123", ctps_uf="PR",
    ctps_data="20/08/2005", escolaridade="08", sit_conjugal="2", freq_escola="N",
    tipo_logradouro="RUA", logradouro="DAS FLORES", numero="123", complemento="APTO 4",
    bairro="CENTRO", mun_res="ASTORGA", ibge_res="410190", uf_res="PR", cep="86730000",
    telefone="44999887766", banco_cod="001", banco_nome="BANCO DO BRASIL", ag_cod="1234",
    ag_nome="ASTORGA CENTRO", conta="123456789012",
)
VINCULOS = [
    dict(registro="123456", orgao="COREN", sus="S", vinc_cod="01", vinc_desc="EMPREGO PUBLICO",
         tipo_cod="1", tipo_desc="CONTRATADO", sub_cod="02", sub_desc="CLT", cbo_cod="223505",
         cbo_desc="ENFERMEIRO", ch_amb="20", ch_hosp="20", ch_outros="0", data_entrada="01/02/2020",
         data_deslig="", motivo_cod="", motivo_desc=""),
    dict(registro="654321", orgao="CRM", sus="N", vinc_cod="03", vinc_desc="AUTONOMO",
         tipo_cod="2", tipo_desc="PROPRIETARIO", sub_cod="05", sub_desc="SUBTIPO TESTE",
         cbo_cod="225125", cbo_desc="MEDICO CLINICO", ch_amb="10", ch_hosp="0", ch_outros="5",
         data_entrada="15/03/2021", data_deslig="30/09/2026", motivo_cod="02",
         motivo_desc="PEDIDO DE DEMISSAO"),
]
