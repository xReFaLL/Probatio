"""
Nettoyage ponctuel — supprime les lignes avec une valeur OHLC manquante déjà
écrites dans l'entrepôt AVANT le correctif de parquet_writer.py (qui empêche
maintenant ces lignes d'être écrites à l'avenir).

Cause typique observée : Yahoo Finance n'avait pas encore finalisé la clôture
du jour pour certaines bourses (ex: Euronext Paris) au moment de l'ingestion
— pas un vrai trou historique, juste une donnée pas encore disponible ce
jour-là. Un futur re-lancement de l'ingestion pour ces symboles récupérera la
vraie valeur une fois publiée par la source.

Usage :
    python packages/data-pipeline/fix_null_ohlc_rows.py
"""
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()
WAREHOUSE_DIR = Path(os.getenv("DATA_WAREHOUSE_DIR", "./data/warehouse"))


def main():
    glob_pattern = (WAREHOUSE_DIR / "*" / "*" / "*" / "*.parquet").as_posix()
    con = duckdb.connect()

    affected = con.execute(f"""
        SELECT DISTINCT filename
        FROM read_parquet('{glob_pattern}', union_by_name=True, filename=True)
        WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
    """).fetchall()

    if not affected:
        print("Aucune ligne avec OHLC manquant trouvée. Rien à nettoyer.")
        con.close()
        return

    print(f"{len(affected)} fichier(s) à nettoyer.")
    for (filename,) in affected:
        tmp_path = Path(filename).with_suffix(".tmp.parquet")
        con.execute(f"""
            COPY (
                SELECT * FROM read_parquet('{filename}')
                WHERE open IS NOT NULL AND high IS NOT NULL
                  AND low IS NOT NULL AND close IS NOT NULL
                ORDER BY timestamp
            ) TO '{tmp_path.as_posix()}' (FORMAT PARQUET)
        """)
        tmp_path.replace(filename)
        print(f"  nettoyé : {filename}")

    con.close()
    print("Terminé.")


if __name__ == "__main__":
    main()