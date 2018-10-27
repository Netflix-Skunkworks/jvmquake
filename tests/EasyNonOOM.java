import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public final class EasyNonOOM
{
    public static void main(String[] args)
    {
        List<Object> list = new ArrayList<>();
        double goodZone = 0.50 * Runtime.getRuntime().maxMemory();
        System.out.println(String.format(
            "Not triggering OutOfMemory by only allocating %.2f bytes",
            goodZone
        ));

        long start = System.nanoTime();
        long end = 0;
        try {
            while (true) {
                if (list.size() * 1024 * 1024 < goodZone)
                {
                    byte[] bytes = new byte[1024 * 1024];
                    list.add(bytes);
                }
                if (TimeUnit.NANOSECONDS.toSeconds(System.nanoTime() - start) > 10)
                    break;
            }
        }
        catch (Exception t) {
            System.out.println(t.toString());
        }
        System.out.println("final list size: " + list.size());
    }
}
