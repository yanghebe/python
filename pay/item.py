from sqlalchemy import Column, DateTime, Integer, String, func, ForeignKey
from database import Base


class Items(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)

    product_id = Column("product_id", ForeignKey("products.id"))
    product_name = Column(String)
    product_price = Column(Integer)
    quantity = Column(Integer)#產品訂購的數量

    created_time = Column(DateTime, default=func.now())#訂單建立的時間

    order_id = Column("order_id", ForeignKey("orders.id"))