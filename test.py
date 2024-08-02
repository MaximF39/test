from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from .models import Orders, Comments, Ordercomresponsible, CustomersList, Customer, Orderresponsible
from .models import Costs, Approvedlists, Favorites
from datetime import date
from django.views.generic import View


# Оптимизация запросов к БД, объединяя их по возможности.
# Улучшение читаемости кода, разъединяя длинные методы на более коротки и логически связанные части кода.
# Необходимо использовать понятные имена для переменных и методов, чтобы код был наиболее понятным и поддерживаемым.
# Необходимо использовать функции для удаления дублирования кода.
# Внесение минимальных комментариев к коду, которые смогут пояснить части логики и причины внесения изменений.

# Базовый класс для работы с заказами
class OrderList(LoginRequiredMixin, View):
    def get_filtered_orders(self, request):
        orders = Orders.objects.all()
        search = request.user.search

        if search.search:
            # Фильтрация по имени или владельцам
            orders = orders.filter(Q(name__icontains=search.search) | Q(searchowners__icontains=search.search))
        else:
            if search.goal:
                orders = orders.filter(goal=True)

            if search.favorite:
                favorite_orders = Favorites.objects.filter(user=request.user).values_list('order__orderid', flat=True)
                orders = orders.filter(orderid__in=favorite_orders)

            if search.manager:
                res = Orderresponsible.objects.filter(user=request.user.search.manager)
                order_res = []
                for i in res:
                    order_res.append(i.orderid.orderid)
                res = Ordercomresponsible.objects.filter(user=request.user.search.manager)
                res = res.exclude(orderid__orderid__in=order_res)
                for i in res:
                    order_res.append(i.orderid.orderid)
                orders = orders.filter(orderid__in=order_res)

            if search.stage:
                orders = orders.filter(stageid=request.user.search.stage)

            if search.company:
                orders = orders.filter(Q(cityid=None) | Q(cityid=request.user.search.company))

            if search.customer:
                orders = orders.filter(searchowners__icontains=request.user.search.customer)


class OrderList(BaseOrderView):
    def get(self, request):
        orders = self.get_filtered_orders(request)

        if request.GET.get('action') == 'count':
            return JsonResponse({'count': orders.count()})

        orders = orders.order_by('-reiting')[int(request.GET['start']):int(request.GET['stop'])]

        # создаем списки для хранения данных
        customers, lastcontact, resp, favorite, task = [], [], [], [], []

        for order in orders:
            # получаем список клиентов
            customers_list = CustomersList.objects.filter(orderid=order.orderid).order_by('customerid__title')
            customers.append(customers_list)

            # последний контакт
            last_contact = Comments.objects.filter(orderid=order).first()
            lastcontact.append(last_contact.createdat if last_contact else '')

            # Задачи
            task.append(Comments.objects.filter(orderid=order, istask=True).exclude(complete=True).count())
            resp.append(Orderresponsible.objects.filter(orderid=order.orderid))

            # Проверка избранного
            favorite.append(Favorites.objects.filter(user=request.user, order=order).exists())

        context = {
            'orders': zip(orders, customers, favorite, lastcontact, task, resp),
            'Today': date.today()
        }

        return render(request, 'main/orders_list.html', context)


class CostList(LoginRequiredMixin, View):
    def get(self, request):
        costs = Costs.objects.all()
        search = request.user.search

        if search.search:
            costs = costs.filter(
                Q(description__icontains=search.search) |
                Q(section__icontains=search.search) |
                Q(orderid__name__icontains=search.search)
            )
        else:
            if search.goal:
                costs = costs.filter(orderid__goal=True)

            if search.favorite:
                fav = Favorites.objects.filter(user=request.user)
                orders_fav = []
                for i in fav:
                    orders_fav.append(i.order.orderid)
                costs = costs.filter(orderid__in=orders_fav)

            if search.manager:
                costs = costs.filter(user=request.user.search.manager)

            if search.stage:
                costs = costs.filter(orderid__stageid=request.user.search.stage)

            if search.company:
                costs = costs.filter(Q(orderid__cityid=None) | Q(orderid__cityid=request.user.search.company))

            if search.customer:
                costs = costs.filter(orderid__searchowners__icontains=request.user.search.customer)

        if request.GET.get('action') == 'count':
            return JsonResponse({'count': costs.count()})

        costs = costs.order_by('-createdat')[int(request.GET['start']):int(request.GET['stop'])]

        # Список утверждений
        appr = [Approvedlists.objects.filter(cost_id=cost) for cost in costs]

        context = {
            'costs': zip(costs, appr),
            'Today': date.today()
        }
        return render(request, 'main/cost_list.html', context)
