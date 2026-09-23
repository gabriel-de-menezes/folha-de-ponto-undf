"""Ponto de entrada: monta os serviços (raiz de composição) e abre a interface."""
from folha_ponto.infraestrutura.container import montar_servicos
from folha_ponto.interface.app import AppDIGEP


def main():
    AppDIGEP(montar_servicos()).mainloop()


if __name__ == "__main__":
    main()
