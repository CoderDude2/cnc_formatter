import sqlite3
from machine_data import MachineData, AbutmentType, Diameter
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent

class DB:
    def __init__(self):
        self.con = sqlite3.connect("machines.db")
        self.cur = self.con.cursor()
    
    def init_db(self):
        self.cur.execute(
            (
                "CREATE TABLE IF NOT EXISTS machines ("
                    "machine_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "machine_number INTEGER NOT NULL UNIQUE,"
                    "supported_diameter INTEGER NOT NULL,"
                    "supported_abutment INTEGER NOT NULL,"
                    "ending_machine_code TEXT)"
            )
        )
        self.con.commit()
    
    def get_machine_id(self, machine: MachineData) -> int:
        res = self.cur.execute("SELECT machine_id FROM machines WHERE machine_number = ?", (machine.machine_number,))
        return res.fetchone()[0]

    def get_machine_by_machine_number(self, machine_number: int) -> MachineData|None:
        res = self.cur.execute("SELECT machine_number, supported_diameter, supported_abutment, ending_machine_code FROM machines WHERE machine_number = ?", (machine_number, )).fetchone()
        if not res:
            return None
        return MachineData(res[0], Diameter(res[1]), AbutmentType(res[2]), res[3])

    def get_all_machines(self) -> list[MachineData]:
        machines:list[MachineData] = []

        res = self.cur.execute("SELECT machine_number, supported_diameter, supported_abutment, ending_machine_code FROM machines ORDER BY machine_number ASC")

        for row in res.fetchall():
            machines.append(MachineData(row[0], Diameter(row[1]), AbutmentType(row[2]), row[3]))

        return machines

    def add_machine(self, machine: MachineData) -> None:
        self.cur.execute("INSERT INTO machines (machine_number, supported_diameter, supported_abutment, ending_machine_code) VALUES (?, ?, ?, ?)", (
            machine.machine_number,
            machine.supported_diameter.value,
            machine.supported_abutment.value,
            machine.ending_machine_code,
        ))

    def update_machine(self, machine: MachineData) -> None:
        machine_id: int = self.get_machine_id(machine)
        self.cur.execute((
            "UPDATE machines SET "
            "machine_number = ?,"
            "supported_diameter = ?,"
            "supported_abutment = ?,"
            "ending_machine_code = ?"
            "WHERE "
                "machine_id = ?"),
            (
                machine.machine_number,
                machine.supported_diameter.value,
                machine.supported_abutment.value,
                machine.ending_machine_code,
                machine_id,
            )
        )
    
    def delete_machine(self, machine: MachineData) -> None:
        machine_id: int = self.get_machine_id(machine)
        self.cur.execute(("DELETE FROM machines WHERE machine_id = ?"), (machine_id,))

if __name__ == "__main__":
    md: MachineData = MachineData(1, Diameter.PI14, AbutmentType.DS, "this is ending text")
    md2: MachineData = MachineData(2, Diameter.PI10, AbutmentType.ASC, "ASC ending text")
    db: DB = DB()
    db.init_db()

    db.add_machine(md)
    db.add_machine(md2)
    db.con.commit()
    db.update_machine(MachineData(2, Diameter.PI10, AbutmentType.AOT_AND_TLOC, "AOT&TLOC ending text"))
    db.delete_machine(md)
    db.add_machine(md)
    for m in db.get_all_machines():
        print(db.get_machine_id(m), m)
    print(db.get_machine_id(md2))
    print(db.get_machine_by_machine_number(1))
    