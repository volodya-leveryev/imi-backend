import datetime

from django.db.models import Q

from . import models
from rest_framework.response import Response
from rest_framework import status


def generate_events(schedule):
    lesson_id = schedule.lesson.id

    semester_begin = models.Lesson.objects.get(pk=lesson_id).semester.study_start
    semester_end = models.Lesson.objects.get(pk=lesson_id).semester.study_end

    """Заполнение event"""
    # startpoint_date = datetime.date.today()
    startpoint_date = semester_begin - datetime.timedelta(days=1)
    if startpoint_date < semester_begin:
        startpoint_date = semester_begin
    if startpoint_date.isoweekday() > schedule.week_day:
        event_date = startpoint_date + datetime.timedelta(days=(7 - startpoint_date.isoweekday())) + \
                     datetime.timedelta(days=schedule.week_day)
    else:
        event_date = startpoint_date + datetime.timedelta(
            days=(schedule.week_day - startpoint_date.isoweekday()))
    weeks_count = (semester_end - event_date).days // 7 + 1
    pairtime_begin = {
        1: datetime.time(8, 0),
        2: datetime.time(9, 50),
        3: datetime.time(11, 40),
        4: datetime.time(14, 00),
        5: datetime.time(15, 50),
        6: datetime.time(17, 40)
    }
    pairtime_end = {
        1: datetime.time(9, 35),
        2: datetime.time(11, 25),
        3: datetime.time(13, 15),
        4: datetime.time(15, 35),
        5: datetime.time(17, 25),
        6: datetime.time(19, 15)
    }
    step = 2
    if schedule.repeat_option == 1:
        if event_date.isocalendar().week % 2 == 0:
            event_date += datetime.timedelta(days=7)
    elif schedule.repeat_option == 2:
        if event_date.isocalendar().week % 2 == 1:
            event_date += datetime.timedelta(days=7)
    else:
        step = 1

    #related_events = models.Event.objects.filter(schedule=schedule.id).filter(begin__gt=datetime.datetime.now())
    related_events = models.Event.objects.filter(schedule=schedule.id).filter(begin__gt=startpoint_date)
    if related_events.exists():
        related_events.delete()

    for i in range(0, weeks_count, step):
        """ Сначала заполнить пустой event, потом заполнить через точки """
        event = models.Event(begin=datetime.datetime.combine(event_date + datetime.timedelta(days=7 * i),
                                                             pairtime_begin[schedule.pair_num]),
                             end=datetime.datetime.combine(event_date + datetime.timedelta(days=7 * i),
                                                           pairtime_end[schedule.pair_num]),
                             lesson=schedule.lesson,
                             room=schedule.room,
                             type=schedule.type,
                             schedule=schedule)
        event.save()


def get_week_events(viewset, request):
    start_date = request.GET['start_date']
    end_date = request.GET['end_date']

    if request.GET['get_by'] == 'group':
        group_id = request.GET['param_id']
        events = models.Event.objects.filter(
            lesson__group__id=group_id,
            begin__range=(start_date, end_date)
        )
        if not events.exists():
            return Response({'error': 'Нет занятий либо такой группы не существует'}, status.HTTP_404_NOT_FOUND)
    elif request.GET['get_by'] == 'lecturer':
        lecturer_id = request.GET['param_id']
        events = models.Event.objects.filter(
            lesson__lecturer__id=lecturer_id,
            begin__range=(start_date, end_date)
        )
        if not events.exists():
            return Response({'error': 'Нет занятий либо такого преподавателя не существует'}, status.HTTP_404_NOT_FOUND)
    elif request.GET['get_by'] == 'room':
        room_id = request.GET['param_id']
        events = models.Event.objects.filter(
            room__id__iexact=room_id,
            begin__range=(start_date, end_date)
        )
        if not events.exists():
            return Response({'error': 'Нет занятий либо такого преподавателя не существует'}, status.HTTP_404_NOT_FOUND)
    else:
        return Response({'error': 'Неверный параметр {\'get_by\'} запроса'})
    serializer = viewset.get_serializer(events, many=True)
    return Response(serializer.data)


    def schedules_by_group(viewset, request):
        pass


""" 
    На выход дает:
                    - event_date - стартовую дату event-а 
                    - weeks_count - количество недель в семестре
"""
def get_event_date_and_weeks_count(group_id, week_day):

    result = dict();

    semester_begin = models.Semester.objects.get(group_id=group_id).study_start
    semester_end = models.Semester.objects.get(group_id=group_id).study_end


    startpoint_date = semester_begin - datetime.timedelta(days=1)

    if startpoint_date < semester_begin:
        startpoint_date = semester_begin

    if startpoint_date.isoweekday() > week_day:
        event_date = startpoint_date + datetime.timedelta(days=(7 - startpoint_date.isoweekday())) + \
                     datetime.timedelta(days=week_day)
    else:
        event_date = startpoint_date + datetime.timedelta(
            days=(week_day - startpoint_date.isoweekday()))

    weeks_count = (semester_end - event_date).days // 7 + 1

    result['start_event_date'] = event_date
    result['weeks_count'] = weeks_count

    return result


def get_pairs_begin_end(pair_num):
    result = dict()
    pairtime_begin = {
        1: datetime.time(8, 0),
        2: datetime.time(9, 50),
        3: datetime.time(11, 40),
        4: datetime.time(14, 00),
        5: datetime.time(15, 50),
        6: datetime.time(17, 40)
    }
    pairtime_end = {
        1: datetime.time(9, 35),
        2: datetime.time(11, 25),
        3: datetime.time(13, 15),
        4: datetime.time(15, 35),
        5: datetime.time(17, 25),
        6: datetime.time(19, 15)
    }

    result['begin'] = pairtime_begin[pair_num]
    result['end'] = pairtime_end[pair_num]

    return result


def get_available_rooms(group_id, week_day, pair_num, repeat_option):
    rooms = models.Room.objects.all()

    event_date = get_event_date_and_weeks_count(group_id, week_day)['start_event_date']
    weeks_count = get_event_date_and_weeks_count(group_id, week_day)['weeks_count']

    pairtime_begin, pairtime_end = get_pairs_begin_end(pair_num)['begin'], get_pairs_begin_end(pair_num)[
        'end']

    if repeat_option == 0:
        step = 1
    else:
        step = 2

    if (repeat_option == 1 and event_date.isocalendar().week % 2 == 0) or \
            (repeat_option == 2 and event_date.isocalendar().week % 2 == 1):
        event_date += datetime.timedelta(days=7)

    for i in range(0, weeks_count, step):
        begin = datetime.datetime.combine(event_date + datetime.timedelta(days=7 * i), pairtime_begin)
        end = datetime.datetime.combine(event_date + datetime.timedelta(days=7 * i), pairtime_end)

        events = models.Event.objects.filter(Q(begin__range=(begin, end))
                                      |
                                      Q(end__range=(begin, end)))
        rooms = rooms.exclude(event__in=events)

    return rooms
