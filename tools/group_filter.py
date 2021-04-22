import httpx
import ujson as json


class GroupHacker:

    def __init__(self, course=2):
        with open('Students.json', 'rb')as f:
            students = json.loads(f.read())
        self.students = {_['studentID']: _['fio'] for _ in students['data']['allStudent'] if _['course'] == course}
        groups = [[_] for _ in range(37988, 37994)]
        info = {
            'FR1': [],
            'FR2': [],
            'FR3': [],
            'FR4': [],
            'FR5': [],
            'FR6': [],
        }
        i = 1
        for student_id, fio in self.students.items():
            print(i)
            fr = [_['info']['groupName']
                  for _ in httpx.get(f'https://edu.donstu.ru/api/RaspManager?studentID={student_id}', timeout=10).json()['data']['raspList']
                  if _['groupsIDs'] in groups]
            if len(fr) != 0:
                fr = fr[0]
            else:
                print(f'{fio} was kicked')
                continue
            print(f'{fr} - {fio}')
            if fr:
                info[fr].append(fio)
            # sleep(0.2)
            i += 1
        from pprint import pprint
        pprint(info)

