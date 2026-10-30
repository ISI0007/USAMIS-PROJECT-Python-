"""Layer 3 directory presentation data; no passwords or contact secrets."""
from ..repositories.people_repository import directory_records


def directory():
    students,teachers=directory_records()
    def profile(person,kind):
        return {'id':person.id,'name':person.full_name,'kind':kind,
                'number':person.student_number if kind=='Student' else person.staff_number,
                'avatar':person.user.avatar_path if person.user else None,
                'subtitle':(person.program.name if person.program else 'Student') if kind=='Student' else (person.department.name if person.department else 'Faculty')}
    return [profile(s,'Student') for s in students], [profile(t,'Teacher') for t in teachers]
