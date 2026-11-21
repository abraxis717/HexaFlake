/* Synthetic ABI smoke, not a reproduction of historical trained checkpoints. */
#include "HCA88.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); return 1; } } while(0)
int main(int argc, char **argv) {
    const int32_t rel[8]={0,1,-1,-1,1,2,-1,-1}, rows[3]={0,1,2};
    const int64_t ro[4]={0,1,2,3}; const int32_t members[3]={0,0,0};
    double frames[24]={0}, W[80]={0}, b[8]={0};
    double pool[24]={1}, initial[24]={1}, a[24], z[24], cand[64];
    int32_t count[3], off[4], list[8]; int64_t links=0;
    for (int i=0;i<3;i++) for(int j=0;j<8;j++) frames[8*i+j]=(j==0||j==3||j==4||j==7)?1.:0.;
    b[1]=atanh(.5);
    /* Bounded synthetic bridge: four CGC channels in, four transported channels out. */
    if (argc == 5) {
        memset(pool, 0, sizeof pool);
        for (int j=0;j<4;j++) {
            char *end = NULL;
            pool[j]=strtod(argv[j+1], &end);
            CHECK(end != argv[j+1] && *end == '\0' && isfinite(pool[j]) && fabs(pool[j]) <= 0.5);
        }
        CHECK(awr_execute(2,rel,rel,3,rows,pool,a,z,cand,ro,members,frames,W,b,0,0,0,2,0,count,off,list,&links,0)==0);
        CHECK(links==8);
        printf("%.17g %.17g %.17g %.17g\n",pool[16],pool[17],pool[18],pool[19]);
        return 0;
    }
    CHECK(argc == 1);
    CHECK(awr_abi_version()==4);
    CHECK(awr_fsum_probe((double[]){1e16,1.,-1e16},3)==1.);
    CHECK(awr_execute(2,rel,rel,3,rows,pool,a,z,cand,ro,members,frames,W,b,0,0,0,1,0,count,off,list,&links,0)==0);
    CHECK(links==4 && fabs(pool[0]-.5)<1e-14 && fabs(pool[8]-.25)<1e-14 && pool[16]==0.);
    memcpy(pool,initial,sizeof pool);
    CHECK(awr_execute(2,rel,rel,3,rows,pool,a,z,cand,ro,members,frames,W,b,0,0,0,2,0,count,off,list,&links,0)==0);
    CHECK(links==8 && fabs(pool[0]-.375)<1e-14 && fabs(pool[8]-.25)<1e-14 && fabs(pool[16]-.125)<1e-14);
    for(int i=0;i<24;i++) if(i%8) CHECK(pool[i]==0.);
    memcpy(pool,initial,sizeof pool);
    CHECK(awr_execute(2,rel,rel,3,rows,pool,a,z,cand,ro,members,frames,W,b,0,0,0,2,1,count,off,list,&links,0)==4);
    CHECK(memcmp(pool,initial,sizeof pool)==0);
    puts("HCA88_ABI=4 FSUM=PASS RECURRENT_TRANSPORT=PASS OVERLAP_REJECTION_ATOMIC=PASS");
    return 0;
}
