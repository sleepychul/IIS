using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Linq;
using System.Threading.Tasks;
public class UDP : MonoBehaviour
{
    public Queue<string> ex1 = new Queue<string>();
    // 1. Declare Variables
    Thread receiveThread;
    UdpClient client;

    public int myport = 9996;

    public String targetip = "127.0.0.1";
    public int targetport = 8090;
    public string receivemsg;
    IPEndPoint anyIP;

    // 2. Initialize variables
    protected void Start()
    {
        InitUDP();
    }

    // 3. InitUDP
    protected void InitUDP()
    {
        client = new UdpClient(myport); //1
        anyIP = new IPEndPoint(IPAddress.Any, 0);
        //anyIP = new IPEndPoint(IPAddress.Parse("172.28.112.1"), 0);
        Debug.Log("UDP Initialized");
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
    }

    // 4. Receive Data
    protected void ReceiveData()
    {
        while (true) //2
        {
            try
            {
                //3
                byte[] data = client.Receive(ref anyIP); //4
                receivemsg = Encoding.UTF8.GetString(data); //5
                ex1.Enqueue(receivemsg);
            }
            catch (Exception e)
            {
                //print(e.ToString());
            }
        }
    }
    void Update()
    {
    }

    void dealqueue()
    {
        while (ex1.Count > 0)
        {
            string receivedmsg = ex1.Dequeue();
        }
    }

    public string DequeueMsg()
    {
        string receivedmsg = ex1.Dequeue();
        return receivedmsg;
    }

    public void Sendmsg(String msg)
    {
        byte[] datagram = Encoding.UTF8.GetBytes(msg);
        //Debug.Log(msg);
        client.Send(datagram, datagram.Length, targetip, targetport);
    }

    public void Sendmsg(String msg, int targetport)
    {
        byte[] datagram = Encoding.UTF8.GetBytes(msg);
        //Debug.Log(msg);
        client.Send(datagram, datagram.Length, targetip, targetport);
    }

    public void Sendmsg(String msg, String targetip, int targetport)
    {
        byte[] datagram = Encoding.UTF8.GetBytes(msg);
        //Debug.Log(msg);
        client.Send(datagram, datagram.Length, targetip, targetport);
    }

    protected void OnApplicationQuit()
    {
        Debug.Log("프로그램 종료");
        client.Close();
        receiveThread.Abort();
    }
}