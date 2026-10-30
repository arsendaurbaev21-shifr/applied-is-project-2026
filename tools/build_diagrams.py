"""Readable ER views with explicitly routed, non-crossing connectors."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def build():
    out=Path(__file__).resolve().parents[1]/'docs/diagrams';out.mkdir(exist_ok=True)
    regular=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',27)
    bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',28)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    def draw(name,title,nodes,edges):
        im=Image.new('RGB',(1500,1000),'white');d=ImageDraw.Draw(im)
        d.text((55,22),title,font=bold,fill='#17354c')
        for points,label,xy in edges:
            d.line(points,fill='#527389',width=3)
            x,y=points[-1];px,py=points[-2];dx=0 if x==px else (1 if x>px else -1);dy=0 if y==py else (1 if y>py else -1)
            d.polygon([(x,y),(x-14*dx+7*dy,y-14*dy-7*dx),(x-14*dx-7*dy,y-14*dy+7*dx)],fill='#527389')
        for x,y,w,en,kz in nodes:
            d.rounded_rectangle((x,y,x+w,y+100),radius=9,fill='#edf4f8',outline='#a7bfce',width=2)
            d.rectangle((x+2,y+2,x+w-2,y+43),fill='#17354c')
            d.text((x+12,y+7),en,font=bold,fill='white');d.text((x+12,y+56),kz,font=regular,fill='#17354c')
        for points,label,xy in edges:
            box=d.multiline_textbbox(xy,label,font=small,spacing=3)
            d.rectangle((box[0]-4,box[1]-3,box[2]+4,box[3]+3),fill='white')
            d.multiline_text(xy,label,font=small,fill='#527389',spacing=3)
        im.save(out/name)
    draw('er-orders.png','Тапсырыс және баға байланыстары',[
        (80,280,280,'Clients','Клиенттер'),(600,100,280,'Cities','Қалалар'),(1100,100,300,'VehicleTypes','Көлік түрлері'),
        (600,280,280,'Routes','Бағыттар'),(1100,280,300,'Tariffs','Тарифтер'),(600,560,280,'Orders','Тапсырыстар'),
        (600,820,280,'CargoItems','Жүк позициялары'),(1100,820,300,'CargoTypes','Жүк түрлері')],[
        ([(740,200),(740,280)],'2 × 1 : N',(770,225)),
        ([(1250,200),(1250,280)],'1 : N',(1270,225)),
        ([(220,380),(220,610),(600,610)],'1 : N',(340,575)),
        ([(740,380),(740,560)],'1 : N',(760,450)),
        ([(1250,380),(1250,610),(880,610)],'1 : N',(1000,575)),
        ([(740,660),(740,820)],'1 : N',(760,730)),
        ([(1100,870),(880,870)],'1 : N',(965,835))])
    draw('er-operations.png','Рейс және есеп байланыстары',[
        (600,100,280,'VehicleTypes','Көлік түрлері'),(600,300,280,'Vehicles','Көліктер'),(1100,300,300,'Drivers','Жүргізушілер'),
        (80,560,280,'Orders','Тапсырыстар'),(600,560,280,'Trips','Рейстер'),(80,820,280,'Payments','Төлемдер'),
        (1020,820,380,'OrderStatusHistory','Мәртебелер тарихы')],[
        ([(740,200),(740,300)],'1 : N',(760,235)),
        ([(740,400),(740,560)],'1 : N',(760,460)),
        ([(1250,400),(1250,610),(880,610)],'1 : N',(1050,575)),
        ([(360,610),(600,610)],'1 : 0..1',(420,575)),
        ([(220,660),(220,820)],'1 : N',(240,725)),
        ([(360,640),(440,640),(440,870),(1020,870)],'1 : N',(670,835))])
    draw('er-accounts.png','Аккаунттар құжаттар және қолдау',[
        (80,100,300,'Clients','Клиенттер'),(600,100,300,'Users','Аккаунттар'),(80,400,300,'Orders','Тапсырыстар'),
        (80,760,300,'Documents','Құжаттар'),(600,400,340,'SupportTickets','Қолдау өтініштері'),
        (1100,400,300,'Orders','Тапсырыстар'),(600,760,340,'TicketMessages','Қолдау хаттары')],[
        ([(380,150),(600,150)],'1 : 0..1',(435,115)),
        ([(750,200),(750,400)],'1 : N',(770,285)),
        ([(600,180),(460,180),(460,810),(380,810)],'1 : N',(470,640)),
        ([(900,150),(1460,150),(1460,810),(940,810)],'1 : N',(1130,775)),
        ([(230,500),(230,760)],'1 : N\nFK NULL',(250,600)),
        ([(1100,450),(940,450)],'1 : N\nFK NULL',(965,385)),
        ([(770,500),(770,760)],'1 : N',(790,620))])

if __name__=='__main__':build()
